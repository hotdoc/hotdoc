# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""A gobject-introspection extension for Hotdoc.

This extension parses a .gir file and extract comments from specified
source files. Parsing the comments ourself allows us to smartly build
the index based on the comments location.
"""

import os

from lxml import etree
from collections import defaultdict
from collections import OrderedDict

from hotdoc.core.symbols import *
from hotdoc.core.extension import Extension, ExtDependency
from hotdoc.core.links import Link, LinkResolver
from hotdoc.core.tree import Page
from hotdoc.core.comment import Comment
from hotdoc.core.exceptions import InvalidOutputException
from hotdoc.utils.loggable import warn, Logger
from hotdoc.utils.utils import OrderedSet

from hotdoc.extensions.gi.formatter import GIFormatter
from hotdoc.extensions.gi.fundamentals import FUNDAMENTALS

from hotdoc.parsers.gtk_doc import GtkDocParser
from hotdoc.extensions.c.utils import CCommentExtractor

from hotdoc.extensions.gi.flags import *
from hotdoc.extensions.gi.utils import *
from hotdoc.extensions.gi.node_cache import (
    SMART_FILTERS, make_translations, get_translation, get_klass_parents,
    get_klass_children, cache_nodes, type_description_from_node,
    is_introspectable, is_callback_type)
from hotdoc.extensions.gi.gtkdoc_links import GTKDOC_HREFS
from hotdoc.extensions.gi.symbols import GIClassSymbol, GIStructSymbol


DESCRIPTION =\
    """
Parse a gir file and add signals, properties, classes
and virtual methods.

Can output documentation for various
languages.

Must be used in combination with the C extension.
"""


# This in order to prioritize gir sources from all subprojects
ALL_GIRS = {}


ALIASED_LINKS = {l: {} for l in OUTPUT_LANGUAGES}


DEFAULT_PAGE = "Miscellaneous.default_page"


DEFAULT_PAGE_COMMENT = """/**
* Miscellaneous.default_page:
* @title: Miscellaneous
* @short-description: Miscellaneous unordered symbols
*
* Unordered miscellaneous symbols that were not properly documented
*/
"""


Logger.register_warning_code('no-location-indication', InvalidOutputException,
                             'gi-extension')


class GIExtension(Extension):
    extension_name = "gi-extension"
    argument_prefix = "gi"

    def __init__(self, app, project):
        Extension.__init__(self, app, project)

        self.languages = None

        self.__all_sources = None
        self.__current_output_filename = None
        self.__class_gtype_structs = {}
        self.__default_page = DEFAULT_PAGE
        self.__relocated_symbols = set()
        self.created_symbols = set()
        self.__raw_comment_parser = GtkDocParser(self.project)
        self.__c_comment_extractor = CCommentExtractor(
            self, self.__raw_comment_parser)

    # Static vmethod implementations

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('GObject-introspection extension',
                                          DESCRIPTION)
        GIExtension.add_index_argument(group)
        GIExtension.add_sources_argument(group, allow_filters=False)
        GIExtension.add_sources_argument(
            group, prefix='gi-c', add_root_paths=True)
        group.add_argument("--languages", action="store",
                           nargs='*',
                           help="Languages to translate documentation in %s"
                           ", default is to make all languages" % str(
                               OUTPUT_LANGUAGES))

    @staticmethod
    def get_dependencies():
        return [ExtDependency('c-extension', is_upstream=True, optional=True)]

    # Chained-up vmethod overrides

    def parse_config(self, config):
        super(GIExtension, self).parse_config(config)
        ALL_GIRS.update({os.path.basename(s): s for s in self.sources})
        self.c_sources = config.get_sources('gi-c')
        self.source_roots = OrderedSet(config.get_paths('gi_c_source_roots'))
        self.languages = [l.lower() for l in config.get(
            'languages', [])]
        # Make sure C always gets formatted first
        if 'c' in self.languages:
            self.languages.remove('c')
            self.languages.insert(0, 'c')
        if not self.languages:
            self.languages = OUTPUT_LANGUAGES
        for gir_file in self.sources:
            gir_root = etree.parse(gir_file).getroot()
            cache_nodes(gir_root, ALL_GIRS)

    def __formatting_page(self, formatter, page):
        if ALL_GIRS:
            page.meta['extra']['gi-languages'] = ['c', 'python', 'javascript']

    def __list_relocated_symbols(self):
        for comment in self._get_toplevel_comments():
            self.__relocated_symbols |= set(comment.meta.get('symbols', []))
            self.__relocated_symbols |= set(comment.meta.get('private-symbols', []))

    def setup(self):
        for ext in self.project.extensions.values():
            ext.formatter.formatting_page_signal.connect(
                self.__formatting_page)
        commonprefix = os.path.commonprefix(list(self._get_all_sources()))
        self.__default_page = os.path.join(os.path.dirname(commonprefix),
                                           DEFAULT_PAGE)

        super(GIExtension, self).setup()

        self.app.link_resolver.resolving_link_signal.connect_after(
            self.__translate_link_ref, 'default')
        if not self.sources:
            return

        self.__scan_comments()
        self.__list_relocated_symbols()
        self.__scan_sources()
        self.__create_macro_symbols()

    def format_page(self, page, link_resolver, output):
        link_resolver.get_link_signal.connect(self.search_online_links)

        prev_l = None
        page.meta['extra']['gi-languages'] = ','.join(self.languages)
        page.meta['extra']['gi-language'] = 'c'
        Extension.format_page(self, page, link_resolver, output)
        page.meta['extra']['gi-language'] = self.languages[0]

        link_resolver.get_link_signal.disconnect(self.search_online_links)

    def write_out_page(self, output, page):
        prev_l = None
        page.meta['extra']['gi-language'] = 'c'
        Extension.write_out_page(self, output, page)

    def __symbol_is_relocated(self, unique_name, parent_name):
        if unique_name in self.__relocated_symbols:
            return True

        if parent_name in self.__relocated_symbols:
            return True

        return False

    def create_symbol(self, *args, **kwargs):
        args = list(args)
        node = None
        if len(args) > 1:
            node = args.pop(1)
        aliases = kwargs.get('aliases', [])

        unique_name = kwargs.get('unique_name', kwargs.get('display_name'))
        comment = self.app.database.get_comment(unique_name)
        if comment:
            if 'attributes' in comment.annotations:
                if comment.annotations['attributes'].argument.get('doc.skip') is not None:
                    return None

        filename = kwargs.get('filename', self.__default_page)
        if filename == self.__default_page:
            parent_name = kwargs.get('parent_name')
            if not self.__symbol_is_relocated(unique_name, parent_name):
                name = kwargs['display_name']
                kwargs['filename'] = self.__get_symbol_filename(unique_name, node)
                if kwargs.get('filename', self.__default_page) == self.__default_page:
                    self.warn("no-location-indication",
                            "No way to determine where %s should land"
                            " putting it to %s."
                            " Document the symbol for smart indexing to work" % (
                                name, os.path.basename(self.__default_page)))

        res = super(GIExtension, self).create_symbol(*args, **kwargs)

        if res:
            self.created_symbols.add(res.unique_name)

            if node is not None:
                make_translations(res.unique_name, node)
                for alias in aliases:
                    make_translations(alias, node)

        return res

    # VMethod implementations

    def _make_formatter(self):
        return GIFormatter(self)

    def _get_smart_index_title(self):
        return 'GObject API Reference'

    def _get_smart_filename(self, filename):
        if filename == self.__default_page:
            return filename
        return os.path.splitext(filename)[0]

    def _get_smart_key(self, symbol):
        if symbol.filename == self.__default_page:
            return symbol.filename
        return os.path.splitext(symbol.filename)[0]

    def _get_comment_smart_key(self, comment):
        return os.path.splitext(comment.filename)[0]

    def _get_all_sources(self):
        if not self.__all_sources:
            self.__all_sources = list({
                s for s in self.c_sources if s.endswith('.h') or
                s.replace('.c', '.h') not in self.c_sources})

        return self.__all_sources

    # Exposed API for dependent extensions

    @classmethod
    def search_online_links(cls, resolver, name):
        href = GTKDOC_HREFS.get(name)
        if href:
            return Link(href, name, name)
        return None

    # setup-time private methods
    def __get_filename_from_gir(self, node):
        source_position = node.find('{http://www.gtk.org/introspection/core/1.0}source-position')
        if source_position is not None:
            filename = source_position.attrib['filename']
            for common_path in self.source_roots:
                path = os.path.join(common_path, filename)
                if path in self.c_sources:
                    return path
        return None

    def __get_symbol_filename(self, unique_name, node=None):
        if self.__current_output_filename:
            return self.__current_output_filename

        comment = self.app.database.get_comment(unique_name)
        if comment and comment.filename:
            return '%s.h' % os.path.splitext(comment.filename)[0]

        if node is not None:
            filename = self.__get_filename_from_gir(node)
            if filename:
                return filename

        return self.__default_page

    def __get_structure_members(self, node, filename, struct_name, parent_name,
                                in_union=False):
        members = []
        for field in node.getchildren():
            if field.tag in [core_ns('record'), core_ns('union')]:
                if 'name' in field.attrib:
                    struct_name = '%s.%s' % (struct_name, field.attrib['name'])

                new_union = field.tag == core_ns('union')
                union_members = self.__get_structure_members(
                    node=field,
                    filename=filename,
                    struct_name=struct_name,
                    parent_name=parent_name,
                    in_union=in_union or new_union)
                members += union_members
                continue
            elif field.tag != core_ns('field'):
                continue

            children = field.getchildren()
            if not children:
                continue

            if field.attrib.get('private', False):
                continue

            if children[0].tag == core_ns('callback'):
                continue

            type_desc = type_description_from_node(field)
            if is_callback_type(type_desc.c_name):
                continue

            field_name = field.attrib['name']
            name = "%s.%s" % (struct_name, field_name)

            qtype = QualifiedSymbol(type_tokens=type_desc.type_tokens)
            self.add_attrs(qtype, type_desc=type_desc)

            member = self.create_symbol(
                FieldSymbol,
                member_name=field_name, qtype=qtype,
                filename=filename, display_name=name,
                unique_name=name, parent_name=parent_name)

            if member:
                self.add_attrs(member, type_desc=type_desc, in_union=in_union)
                members.append(member)

        return members

    def __find_structure_pagename(self, node, unique_name, is_class):
        filename = self.__get_symbol_filename(unique_name, node)
        if filename != self.__default_page:
            return filename

        if self.__symbol_is_relocated(unique_name, None):
            return self.__default_page

        if not is_class:
            sym = self.__class_gtype_structs.get(node.attrib['name'])
            if sym and sym.filename:
                return sym.filename

        filenames = []
        for cnode in node:
            cunique_name = get_symbol_names(cnode)[0]
            if not cunique_name:
                continue
            fname = self.__get_symbol_filename(cunique_name, cnode)
            if fname != self.__default_page:
                if cnode.tag == core_ns('constructor'):
                    filenames.insert(0, fname)
                else:
                    filenames.append(fname)

        unique_filenames = list(OrderedSet(filenames))
        if not filenames:
            # Did not find any symbols, trying to can get information
            # about the class structure linked to that object class.
            nextnode = node.getnext()
            name = node.attrib['name']
            if nextnode is not None and nextnode.tag == core_ns('record'):
                nextnode_classfor = nextnode.attrib.get(glib_ns(
                    'is-gtype-struct-for'))
                if nextnode_classfor == name:
                    nunique_name = get_symbol_names(nextnode)[0]
                    filename = self.__get_symbol_filename(nunique_name)

            if filename == self.__default_page:
                self.warn("no-location-indication",
                          "No way to determine where %s should land"
                          " putting it to %s."
                          " Document the symbol for smart indexing to work" % (
                              unique_name, os.path.basename(filename)))
        else:
            filename = unique_filenames[0]
            if len(unique_filenames) > 1:
                self.warn("no-location-indication",
                          " Going wild here to determine where %s needs to land"
                          " as we could detect the following possibilities: %s."
                          % (unique_name, unique_filenames))
            else:
                self.debug(" No class comment for %s determined that it should"
                           " land into %s with all other class related documentation."
                           % (unique_name, os.path.basename(filename)))

        return filename

    def __sort_parameters(self, symbol, retval, parameters):
        in_parameters = []
        out_parameters = []

        for i, param in enumerate(parameters):
            if isinstance(symbol, MethodSymbol) and i == 0:
                continue

            direction = self.get_attr(param, 'direction')

            if direction == 'in' or direction == 'inout':
                in_parameters.append(param)
            if direction == 'out' or direction == 'inout':
                out_parameters.append(param)

        self.add_attrs(symbol, parameters=in_parameters)

    def __create_parameter_symbol(self, gi_parameter):
        param_name = gi_parameter.attrib['name']

        type_desc = type_description_from_node(gi_parameter)
        direction = gi_parameter.attrib.get('direction')
        if direction is None:
            direction = 'in'

        res = ParameterSymbol(argname=param_name,
                              type_tokens=type_desc.type_tokens)
        self.add_attrs(res, type_desc=type_desc, direction=direction)

        return res, direction

    def __create_return_value_symbol(self, gi_retval, out_parameters):
        type_desc = type_description_from_node(gi_retval)

        if type_desc.gi_name == 'none':
            ret_item = None
        else:
            ret_item = ReturnItemSymbol(type_tokens=type_desc.type_tokens)
            self.add_attrs(ret_item, type_desc=type_desc)

        res = [ret_item]

        for out_param in out_parameters:
            ret_item = ReturnItemSymbol(type_tokens=out_param.input_tokens,
                                        name=out_param.argname)
            self.add_attrs(ret_item, type_desc=self.get_attr(
                out_param, 'type_desc'))

            res.append(ret_item)

        return res

    def __create_parameters_and_retval(self, node):
        gi_parameters = node.find(
            '{http://www.gtk.org/introspection/core/1.0}parameters')

        if gi_parameters is None:
            instance_param = None
            gi_parameters = []
        else:
            instance_param = \
                gi_parameters.find(
                    '{http://www.gtk.org/introspection/core/1.0}instance-parameter')
            gi_parameters = gi_parameters.findall(
                '{http://www.gtk.org/introspection/core/1.0}parameter')

        parameters = []

        if instance_param is not None:
            param, direction = self.__create_parameter_symbol(instance_param)
            parameters.append(param)

        out_parameters = []
        for gi_parameter in gi_parameters:
            param, direction = self.__create_parameter_symbol(gi_parameter)
            parameters.append(param)
            if direction != 'in':
                out_parameters.append(param)

        if node.attrib.get('throws') == '1':
            type_desc = SymbolTypeDesc([Link(None, 'GError', 'GError'), '*', '*'], 'GLib.Error', 'GError**', 0)
            param = ParameterSymbol(argname='error', type_tokens=type_desc.type_tokens)
            parameters.append(param)
            self.add_attrs(param, type_desc=type_desc, direction='out')

        retval = node.find(
            '{http://www.gtk.org/introspection/core/1.0}return-value')
        retval = self.__create_return_value_symbol(retval, out_parameters)

        return (parameters, retval)

    def __create_callback_symbol(self, node, parent_name):
        name = node.attrib[c_ns('type')]
        parameters, retval = self.__create_parameters_and_retval(node)

        filename = self.__get_symbol_filename(name, node)
        sym = self.create_symbol(
            CallbackSymbol, node, parameters=parameters,
            return_value=retval, display_name=name,
            filename=filename, parent_name=parent_name)

        if sym:
            self.__sort_parameters(sym, retval, parameters)

        return sym

    def __create_enum_symbol(self, node, spelling=None):
        name = node.attrib[c_ns('type')]

        filename = self.__get_symbol_filename(name, node)
        psymbol = self.app.database.get_symbol(name)
        is_genum = node.attrib.get(glib_ns('type'), False)
        if psymbol:
            if not isinstance(psymbol, EnumSymbol):
                self.warn('symbol-redefined', "EnumSymbol(unique_name=%s, filename=%s, project=%s)"
                    " has already been defined: %s" % (name, filename, self.project.project_name, psymbol))
                return None

            psymbol_is_genum = self.get_attr(psymbol, "is_genum")
            if psymbol_is_genum is None or psymbol_is_genum == is_genum:
                self.warn('symbol-redefined', "EnumSymbol(unique_name=%s, filename=%s, project=%s)"
                     " has already been defined: %s" % (name, filename, self.project.project_name, psymbol))
                return None

            # FIXME Handle nicks in GEnums
            return None

        # FIXME Working around https://gitlab.gnome.org/GNOME/glib/issues/1756
        members = OrderedDict()
        for field in node.findall(core_ns('member')):
            unique_name = field.attrib[c_ns('identifier')]
            if unique_name in members:
                continue
            member = self.create_symbol(
                EnumMemberSymbol, field, display_name=unique_name,
                filename=filename, parent_name=name)

            if member:
                member.enum_value = field.attrib['value']
                members[unique_name] = member

        res = self.create_symbol(
            EnumSymbol, node, members=list(members.values()),
            anonymous=False, display_name=name,
            filename=filename, raw_text=None)

        if res:
            self.add_attrs(res, is_genum=is_genum)

            for cnode in node:
                parent_name = res.unique_name
                if cnode.tag == core_ns('function'):
                    parent_name = None
                self.__scan_node(cnode, parent_name=parent_name)

        return res

    def __create_signal_symbol(self, node, parent_name):
        unique_name, name, klass_name = get_symbol_names(node)

        parameters, retval = self.__create_parameters_and_retval(node)

        parent_node = node.getparent()
        parent_gi_name = get_gi_name(parent_node)
        parent_link = Link(None, parent_name, parent_name)

        instance_param = ParameterSymbol(
            argname='self', type_tokens=[parent_link, '*'])
        type_desc = SymbolTypeDesc([], parent_gi_name, None, 0)
        self.add_attrs(instance_param, type_desc=type_desc, direction='in')
        parameters.insert(0, instance_param)

        udata_link = Link(None, 'gpointer', 'gpointer')
        udata_param = ParameterSymbol(
            argname='user_data', type_tokens=[udata_link])
        type_desc = SymbolTypeDesc([], 'gpointer', None, 0)
        self.add_attrs(udata_param, type_desc=type_desc, direction='in')
        parameters.append(udata_param)

        res = self.create_symbol(SignalSymbol, node,
            parameters=parameters, return_value=retval,
            display_name=name, unique_name=unique_name,
            filename=self.__get_symbol_filename(klass_name, node),
            parent_name=parent_name)

        if res:
            flags = []

            when = node.attrib.get('when')
            if when == "first":
                flags.append(RunFirstFlag())
            elif when == "last":
                flags.append(RunLastFlag())
            elif when == "cleanup":
                flags.append(RunCleanupFlag())

            no_hooks = node.attrib.get('no-hooks')
            if no_hooks == '1':
                flags.append(NoHooksFlag())

            # This is incorrect, it's not yet format time
            extra_content = self.formatter._format_flags(flags)
            res.extension_contents['Flags'] = extra_content

            self.__sort_parameters(res, retval, parameters)

        return res

    def __create_property_symbol(self, node, parent_name):
        unique_name, name, klass_name = get_symbol_names(node)

        type_desc = type_description_from_node(node)
        type_ = QualifiedSymbol(type_tokens=type_desc.type_tokens)
        self.add_attrs(type_, type_desc=type_desc)

        flags = []
        writable = node.attrib.get('writable')
        construct = node.attrib.get('construct')
        construct_only = node.attrib.get('construct-only')

        flags.append(ReadableFlag())
        if writable == '1':
            flags.append(WritableFlag())
        if construct_only == '1':
            flags.append(ConstructOnlyFlag())
        elif construct == '1':
            flags.append(ConstructFlag())

        res = self.create_symbol(PropertySymbol, node,
                                        prop_type=type_,
                                        display_name=name,
                                        unique_name=unique_name,
                                        filename=self.__get_symbol_filename(
                                            klass_name, node),
                                        parent_name=parent_name)

        if res:
            extra_content = self.formatter._format_flags(flags)
            res.extension_contents['Flags'] = extra_content

        return res

    def __create_vfunc_symbol(self, node, parent_name):
        klass_node = node.getparent()
        ns = klass_node.getparent()
        gtype_struct = klass_node.attrib.get(glib_ns('type-struct'))

        klass_comment = self.app.database.get_comment('%s%s' %
                                                      (ns.attrib['name'], gtype_struct))

        unique_name, name, klass_name = get_symbol_names(node)

        # Virtual methods are documented in the class comment
        if klass_comment:
            param_comment = klass_comment.params.get(name)
            if (param_comment):
                self.add_comment(
                    Comment(name=unique_name,
                            meta={'description': param_comment.description},
                            annotations=param_comment.annotations))

        parameters, retval = self.__create_parameters_and_retval(node)
        symbol = self.create_symbol(VFunctionSymbol, node,
                                           parameters=parameters,
                                           return_value=retval, display_name=name,
                                           unique_name=unique_name,
                                           filename=self.__get_symbol_filename(
                                               klass_name, node),
                                           parent_name=parent_name,
                                           aliases=[unique_name.replace('::', '.')])

        if symbol:
            self.__sort_parameters(symbol, retval, parameters)

        return symbol

    def __create_alias_symbol(self, node, gi_name, parent_name):
        name = get_symbol_names(node)[0]

        type_desc = type_description_from_node(node)
        aliased_type = QualifiedSymbol(type_tokens=type_desc.type_tokens)
        self.add_attrs(aliased_type, type_desc=type_desc)
        filename = self.__get_symbol_filename(name, node)

        alias_link = [l for l in type_desc.type_tokens if isinstance(l, Link)]
        for lang in ('python', 'javascript'):
            fund_type = FUNDAMENTALS[lang].get(type_desc.c_name)
            if fund_type:
                # The alias name is now conciderd as a FUNDAMENTAL type.
                FUNDAMENTALS[lang][name] = fund_type
            else:
                if alias_link:
                    ALIASED_LINKS[lang][name] = alias_link[0]

        return self.create_symbol(AliasSymbol, node,
                                         aliased_type=aliased_type,
                                         display_name=name,
                                         filename=filename,
                                         parent_name=parent_name)

    def __create_structure(self, symbol_type, node, gi_name):
        if node.attrib.get(glib_ns('fundamental')) == '1':
            self.debug('%s is a fundamental type, not an actual '
                       'object class' % (node.attrib['name']))
            return

        unique_name, unused_name, klass_name = get_symbol_names(node)
        # Hidding class private structures
        if node.attrib.get('disguised') == '1' and \
                unique_name.endswith(('Priv', 'Private')):
            self.debug('%s seems to be a GObject class private structure, hiding it.'
                       % (unique_name))
            return

        filename = self.__find_structure_pagename(node, unique_name,
                                                  symbol_type == GIClassSymbol)

        self.__current_output_filename = filename
        parent_name = unique_name
        if symbol_type == GIClassSymbol:
            res = self.__create_class_symbol(node, gi_name,
                                             klass_name,
                                             unique_name,
                                             filename)
            class_struct = node.attrib.get(glib_ns('type-struct'))
            if class_struct:
                self.__class_gtype_structs[class_struct] = res
        elif symbol_type == GIStructSymbol:
            # If we are working with a Class structure,
            class_symbol = self.__class_gtype_structs.get(node.attrib['name'])
            if class_symbol:
                parent_name = class_symbol.unique_name

                # Class struct should never be renderer on their own,
                # smart_key will lookup the value in that dict
                self.__class_gtype_structs[unique_name] = class_symbol
            res = self.__create_struct_symbol(node, unique_name, filename,
                                              class_symbol.unique_name if class_symbol else None)

            if class_symbol:
                class_symbol.class_struct_symbol = res
        else:  # Interface
            res = self.__create_interface_symbol(node, unique_name, filename)
            class_struct = node.attrib.get(glib_ns('type-struct'))
            if class_struct:
                self.__class_gtype_structs[class_struct] = res

        for cnode in node:
            if cnode.tag in [core_ns('record'), core_ns('union')]:
                continue
            self.__scan_node(cnode, parent_name=parent_name)

        self.__current_output_filename = None

        return res

    def __create_class_symbol(self, node, gi_name, klass_name,
                              unique_name, filename):
        hierarchy = get_klass_parents(gi_name)
        children = get_klass_children(gi_name)

        members = self.__get_structure_members(node, filename,
                                               klass_name,
                                               unique_name)

        return self.create_symbol(GIClassSymbol, node,
                                        hierarchy=hierarchy,
                                        children=children,
                                        display_name=klass_name,
                                        unique_name=unique_name,
                                        filename=filename,
                                        members=members,
                                        parent_name=unique_name)

    def __create_struct_symbol(self, node, struct_name, filename,
                               parent_name):


        members = self.__get_structure_members(
            node, filename, struct_name,
            parent_name=parent_name or struct_name)

        if not parent_name:
            return self.create_symbol(GIStructSymbol, node,
                                             display_name=struct_name,
                                             unique_name=struct_name,
                                             anonymous=False,
                                             filename=filename,
                                             members=members,
                                             parent_name=struct_name)
        else:
            res = StructSymbol()
            res.display_name = struct_name
            res.unique_name = struct_name
            res.filename = filename
            res.members = members
            return res

    def __create_interface_symbol(self, node, unique_name, filename):
        return self.create_symbol(InterfaceSymbol, node,
                                         display_name=unique_name,
                                         unique_name=unique_name,
                                         parent_name=unique_name,
                                         filename=filename)

    def __create_function_symbol(self, node, parent_name):
        name = get_symbol_names(node)[0]

        gi_params, retval = self.__create_parameters_and_retval(node)

        if node.tag.endswith('method'):
            if node.getparent().attrib.get(glib_ns('is-gtype-struct-for')):
                type_ = ClassMethodSymbol
            else:
                type_ = MethodSymbol
        elif node.tag == core_ns('constructor'):
            type_ = ConstructorSymbol
        else:
            type_ = FunctionSymbol

        func = self.create_symbol(type_, node,
                                         parameters=gi_params,
                                         return_value=retval,
                                         display_name=name,
                                         unique_name=name,
                                         throws='throws' in node.attrib,
                                         filename=self.__get_symbol_filename(
                                             name, node),
                                         parent_name=parent_name)

        if func:
            self.__sort_parameters(func, func.return_value, func.parameters)

        return func

    def __scan_comments(self):
        comment_parser = GtkDocParser(self.project)
        block = self.__raw_comment_parser.parse_comment(DEFAULT_PAGE_COMMENT,
                                                        DEFAULT_PAGE, 0, 0)
        self.add_comment(block)

        self.__c_comment_extractor.parse_comments(self.c_sources)

    def __create_macro_symbols(self):
        self.__c_comment_extractor.create_macro_symbols(SMART_FILTERS, self.c_sources)

    def __scan_node(self, node, parent_name=None):
        gi_name = get_gi_name(node)

        if 'moved-to' in node.attrib:
            return False

        if node.tag == core_ns('class'):
            self.__create_structure(GIClassSymbol, node, gi_name)
        elif node.tag in (core_ns('function'), core_ns('method'), core_ns('constructor')):
            self.__create_function_symbol(node, parent_name)
        elif node.tag == core_ns('virtual-method'):
            self.__create_vfunc_symbol(node, parent_name)
        elif node.tag == core_ns('property'):
            self.__create_property_symbol(node, parent_name)
        elif node.tag == glib_ns('signal'):
            self.__create_signal_symbol(node, parent_name)
        elif node.tag == core_ns('alias'):
            self.__create_alias_symbol(node, gi_name, parent_name)
        elif node.tag == core_ns('record'):
            self.__create_structure(GIStructSymbol, node, gi_name)
        elif node.tag == core_ns('interface'):
            self.__create_structure(InterfaceSymbol, node, gi_name)
        elif node.tag == core_ns('enumeration'):
            self.__create_enum_symbol(node)
        elif node.tag == core_ns('bitfield'):
            self.__create_enum_symbol(node)
        elif node.tag == core_ns('callback'):
            self.__create_callback_symbol(node, parent_name)
        elif node.tag == core_ns('field'):
            pass
        else:
            for cnode in node:
                self.__scan_node(cnode)

    def __scan_sources(self):
        for gir_file in self.sources:
            root = etree.parse(gir_file).getroot()
            self.__scan_node(root)

    # Format-time private methods
    def __translate_ref(self, link, language):
        fund = FUNDAMENTALS[language].get(link.id_)
        if fund:
            return fund.ref

        aliased_link = ALIASED_LINKS[language].get(link.id_)
        if aliased_link:
            return self.__translate_ref(aliased_link, language)

        page = self.project.get_page_for_symbol(link.id_)
        if page:
            if page.extension_name != self.extension_name:
                return None
            return link.ref

        if link.ref is None:
            return GTKDOC_HREFS.get(link.id_)

        return None

    def __translate_title(self, link, language):
        fund = FUNDAMENTALS[language].get(link.id_)
        if fund:
            return fund._title

        if language != 'c' and not is_introspectable(link.id_, language):
            return link._title + ' (not introspectable)'

        aliased_link = ALIASED_LINKS[language].get(link.id_)
        if aliased_link:
            return self.__translate_link_title(aliased_link, language)

        translated = get_translation(link.id_, language)
        if translated:
            return translated

        if language == 'c' and link.id_ in GTKDOC_HREFS:
            return link.id_

        return None

    def __translate_link_ref(self, link, language):
        if language == 'default':
            actual_language = 'c'
        else:
            actual_language = language

        ref = self.__translate_ref(link, actual_language)
        if ref is None:
            return None

        extra_attrs = {}
        if language == 'default':
            extra_attrs['data-gi-href-python'] = self.__translate_ref(
                link, 'python') or ref
            extra_attrs['data-gi-href-javascript'] = self.__translate_ref(
                link, 'javascript') or ref
            extra_attrs['data-gi-title-python'] = self.__translate_title(
                link, 'python')
            extra_attrs['data-gi-title-javascript'] = self.__translate_title(
                link, 'javascript')
        return ref, extra_attrs

    def __translate_link_title(self, link, language):
        return self.__translate_title(link, language)

    def setup_language(self, language, prev_l):
        if prev_l:
            Link.resolving_title_signal.disconnect(self.__translate_link_title,
                                                   prev_l)
            self.app.link_resolver.resolving_link_signal.disconnect(
                self.__translate_link_ref, prev_l)
        else:
            self.app.link_resolver.resolving_link_signal.disconnect(
                self.__translate_link_ref, 'default')

        if language is not None:
            Link.resolving_title_signal.connect(self.__translate_link_title,
                                                language)
            self.app.link_resolver.resolving_link_signal.connect(
                self.__translate_link_ref, language)
        else:
            self.app.link_resolver.resolving_link_signal.connect_after(
                self.__translate_link_ref, 'default')
