# -*- coding: utf-8 -*-
#
# Copyright © 2018 Thibault Saunier <tsaunier@igalia.com>
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

import re
import os
import json
import html

from tempfile import TemporaryDirectory

from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.ext.code import CodeExtension
from wheezy.template.loader import FileLoader
from hotdoc.extensions import gi
from hotdoc.extensions.gi.gi_extension import GIExtension
from hotdoc.core.links import Link
from hotdoc.utils.loggable import info, Logger, error
from hotdoc.utils.utils import OrderedSet
from hotdoc.core.extension import Extension
from hotdoc.core.symbols import ClassSymbol, QualifiedSymbol, PropertySymbol, \
    SignalSymbol, ReturnItemSymbol, ParameterSymbol, Symbol
from hotdoc.parsers.gtk_doc import GtkDocParser
from hotdoc.extensions.c.utils import CCommentExtractor
from hotdoc.core.exceptions import HotdocSourceException
from hotdoc.core.formatter import Formatter
from hotdoc.core.comment import Comment
from hotdoc.extensions.gi.gi_extension import WritableFlag, ReadableFlag, \
    ConstructFlag, ConstructOnlyFlag
from hotdoc.extensions.gi.fundamentals import FUNDAMENTALS

Logger.register_warning_code('signal-arguments-mismatch', HotdocSourceException,
                             'gst-extension')

DESCRIPTION =\
    """
Extract gstreamer plugin documentation from sources and
built plugins.
"""


def _cleanup_package_name(package_name):
    return package_name.strip(
        'git').strip('release').strip(
            'prerelease').strip(
                'GStreamer').strip(
                    'Plug-ins').strip(' ')


def create_hierarchy(element_dict):

    hierarchy = []

    for klass_name in element_dict["hierarchy"][1:]:
        link = Link(None, klass_name, klass_name)
        sym = QualifiedSymbol(type_tokens=[link])
        hierarchy.append(sym)

    hierarchy.reverse()
    return hierarchy


def type_tokens_from_type_name(type_name):
    res = [Link(None, type_name, type_name)]
    if type_name not in FUNDAMENTALS['python']:
        res.append('<span class="pointer-token">*</span>')
    return res


class GstPluginsSymbol(Symbol):
    TEMPLATE = """
        @require(symbol, unique_feature)
        @if not unique_feature:
            <div class="base_symbol_container">
            <table class="table table-striped table-hover">
                <tbody>
                    <tr>
                        <th class="col-md-2"><b>Name</b></th>
                        <th class="col-md-2"><b>Classification</b></th>
                        <th class="col-md-4"><b>Description</b></th>
                    </tr>
                    @for elem in symbol.get_elements():
                        <tr>
                            <td>@elem.rendered_link</td>
                            <td>@elem.classification.replace('/', ' ')</td>
                            <td>@elem.desc</td>
                        </tr>
                    @end
                    @end
                </tbody>
            </table>
            </div>
            @end
        @end
        """
    __tablename__ = 'gst_plugins'

    def __init__(self, **kwargs):
        self.name = None
        self.description = None
        self.plugins = []
        self.elems = []
        self.all_plugins = False
        Symbol.__init__(self, **kwargs)

    def get_elements(self):
        all_elements = []
        for plugin in self.plugins:
            for elem in plugin.elements:
                all_elements.append(elem)

        return sorted(all_elements, key=lambda x: x.display_name)

    def get_children_symbols(self):
        return self.plugins

    @classmethod
    def get_plural_name(cls):
        return ""


class GstElementSymbol(ClassSymbol):
    TEMPLATE = """
        @require(symbol, hierarchy, desc)
        @desc

        @if hierarchy:
        <h2>Hierarchy</h2>
        <div class="hierarchy_container">
            @hierarchy
        </div>
        @end
        <h2 class="symbol_section">Factory details</h2>
        <div class="symbol-detail">
            <p><b>Authors:</b> – @symbol.author</p>
            <p><b>Classification:</b> – <code>@symbol.classification</code></p>
            <p><b>Rank</b> – @symbol.rank</p>
            <p><b>Plugin</b> – @symbol.plugin</p>
            <p><b>Package</b> – @symbol.package</p>
        </div>
        @end
        """
    __tablename__ = 'gst_element'

    def __init__(self, **kwargs):
        self.classification = None
        self.rank = None
        self.author = None
        self.plugin = None
        ClassSymbol.__init__(self, **kwargs)

    @classmethod
    def get_plural_name(cls):
        return ""


class GstPluginSymbol(Symbol):
    TEMPLATE = """
        @require(symbol, unique_feature)
        @if not unique_feature:
        <h1>@symbol.display_name</h1>
        <i>(from @symbol.package)</i>
        @end
        <div class="base_symbol_container">
        @symbol.formatted_doc
        @if not unique_feature:
        <table class="table table-striped table-hover">
            <tbody>
                <tr>
                    <th><b>Name</b></th>
                    <th><b>Classification</b></th>
                    <th><b>Description</b></th>
                </tr>
                @for elem in symbol.elements:
                    <tr>
                        <td>@elem.rendered_link</td>
                        <td>@elem.classification</td>
                        <td>@elem.desc</td>
                    </tr>
                @end
            </tbody>
        </table>
        @end
        </div>
        @end
        """
    __tablename__ = 'gst_plugin'

    def __init__(self, **kwargs):
        self.name = None
        self.license = None
        self.description = None
        self.package = None
        self.elements = []
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.elements

    @classmethod
    def get_plural_name(cls):
        return ""


class GstNamedConstantValue(Symbol):
    __tablename__ = 'named constants value'
    TEMPLATE = """
        @require(symbol)
        <div class="member_details" class="always-hide-toc" data-toc-skip=true data-hotdoc-id="@symbol.link.id_">
        <code>@symbol.val['name']</code> (<i>@symbol.val['value']</i>) – @symbol.val['desc']
        </div>
    """


class GstNamedConstantsSymbols(Symbol):
    __tablename__ = 'named constants'

    def __init__(self, **kwargs):
        self.members = {}
        self.raw_text = ''
        self.anonymous = False
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.members

    def get_extra_links(self):
        return [m.link for m in self.members]

    def get_type_name(self):
        return "Name constant"

    @classmethod
    def get_plural_name(cls):
        return 'Named constants'


class GstPadTemplateSymbol(Symbol):
    TEMPLATE = """
        @extends('base_symbol.html')
        @require(symbol)

        @def header():
        <h3><span><code>@symbol.name</code></span></h3>
        @end
        @def content():
        <div>
            <pre class="language-yaml"><code class="language-yaml">@symbol.caps</code></pre>
            <div class="symbol-detail">
                <p><b>Presence</b> – <i>@symbol.presence</i></p>
                <p><b>Direction</b> – <i>@symbol.direction</i></p>
                @if symbol.object_type:
                    <p><b>Object type</b> – @symbol.object_type.rendered_link</p>
                @end
            </div>
        </div>
        @end
        """

    __tablename__ = 'pad_templates'

    def __init__(self, **kwargs):
        self.qtype = None
        self.name = None
        self.direction = None
        self.presence = None
        self.caps = None
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return [self.qtype]

    # pylint: disable=no-self-use
    def get_type_name(self):
        """
        Banana banana
        """
        return "GstPadTemplate"


class GstFormatter(Formatter):
    engine = None

    def __init__(self, extension):
        self.__tmpdir = TemporaryDirectory()
        with open(os.path.join(self.__tmpdir.name, "padtemplate.html"), "w") as _:
            _.write(GstPadTemplateSymbol.TEMPLATE)
        with open(os.path.join(self.__tmpdir.name, "enumtemplate.html"), "w") as _:
            _.write(GstNamedConstantValue.TEMPLATE)
        with open(os.path.join(self.__tmpdir.name, "plugins.html"), "w") as _:
            _.write(GstPluginsSymbol.TEMPLATE)
        with open(os.path.join(self.__tmpdir.name, "plugin.html"), "w") as _:
            _.write(GstPluginSymbol.TEMPLATE)
        with open(os.path.join(self.__tmpdir.name, "element.html"), "w") as _:
            _.write(GstElementSymbol.TEMPLATE)
        Formatter.__init__(self, extension)
        self._order_by_parent = True
        self._ordering.insert(0, GstPluginSymbol)
        self._ordering.insert(1, GstElementSymbol)
        self._ordering.insert(self._ordering.index(
            ClassSymbol) + 1, GstPadTemplateSymbol)
        self._ordering.insert(self._ordering.index(GstPadTemplateSymbol) + 1,
                              GstPluginsSymbol)
        self._ordering.append(GstNamedConstantsSymbols)

        self._symbol_formatters.update(
            {GstPluginsSymbol: self._format_plugins_symbol,
             GstPluginSymbol: self._format_plugin_symbol,
             GstPadTemplateSymbol: self._format_pad_template_symbol,
             GstElementSymbol: self._format_element_symbol,
             GstNamedConstantsSymbols: self._format_enum,
             GstNamedConstantValue: self._format_name_constant_value, })

    def get_template(self, name):
        return GstFormatter.engine.get_template(name)

    def parse_toplevel_config(self, config):
        super().parse_toplevel_config(config)
        if GstFormatter.engine is None:
            gi_extension_path = gi.__path__[0]

            searchpath = [os.path.join(gi_extension_path, "html_templates"),
                          self.__tmpdir.name] + Formatter.engine.loader.searchpath
            GstFormatter.engine = Engine(
                loader=FileLoader(searchpath, encoding='UTF-8'),
                extensions=[CoreExtension(), CodeExtension()])
            GstFormatter.engine.global_vars.update({'e': html.escape})

    def __del__(self):
        self.__tmpdir.cleanup()

    def __populate_plugin_infos(self, plugin):
        if not plugin.description:
            comment = self.extension.app.database.get_comment(
                plugin.unique_name)
            plugin.description = comment.description if comment else ''
        plugin.rendered_link = self._format_linked_symbol(plugin)
        for element in plugin.elements:
            comment = self.extension.app.database.get_comment(
                'element-' + element.unique_name)

            element.plugin_rendered_link = plugin.rendered_link
            element.license = plugin.license
            element.rendered_link = self._format_linked_symbol(element)
            if not comment:
                element.desc = "%s element" % element.display_name
                continue

            if not comment.short_description:
                desc = "%s element" % (element.display_name)
            else:
                desc = comment.short_description.description
            element.desc = desc

    def _format_page(self, page):
        # In our case unparented sections should go first one
        page.by_parent_symbols.move_to_end(None, last=False)

        return super()._format_page(page)

    def _format_prototype(self, function, is_pointer, title):
        c_proto = Formatter._format_prototype(self, function, is_pointer, title)
        template = self.get_template('python_prototype.html')
        python_proto = template.render(
            {'function_name': title,
             'parameters': function.parameters,
             'throws': False,
             'comment': "python callback for the '%s' signal" % function.make_name(),
             'is_method': False})
        template = self.get_template('javascript_prototype.html')
        for param in function.parameters:
            param.extension_contents['type-link'] = self._format_linked_symbol(
                param)
        js_proto = template.render(
            {'function_name': title,
             'parameters': function.parameters,
             'throws': False,
             'comment': "javascript callback for the '%s' signal" % function.make_name(),
             'is_method': False})
        for param in function.parameters:
            param.extension_contents.pop('type-link', None)
        return '%s%s%s' % (c_proto, python_proto, js_proto)

    def _format_plugins_symbol(self, symbol):
        for plugin in symbol.plugins:
            self.__populate_plugin_infos(plugin)
        template = self.engine.get_template('plugins.html')
        return template.render({'symbol': symbol,
                                'unique_feature': self.extension.unique_feature})

    def _format_plugin_symbol(self, symbol):
        self.__populate_plugin_infos(symbol)
        template = self.engine.get_template('plugin.html')
        return template.render({'symbol': symbol,
                                'unique_feature': self.extension.unique_feature})

    def _format_pad_template_symbol(self, symbol):
        template = self.engine.get_template('padtemplate.html')
        if symbol.object_type:
            symbol.object_type.rendered_link = self._format_linked_symbol(
                symbol.object_type)
        return template.render({'symbol': symbol})

    def _format_element_symbol(self, symbol):
        hierarchy = self._format_hierarchy(symbol)

        template = self.engine.get_template('element.html')
        return template.render({'symbol': symbol, 'hierarchy': hierarchy, 'desc': ''})

    def _format_name_constant_value(self, symbol):
        template = self.engine.get_template('enumtemplate.html')
        return template.render({'symbol': symbol})

    def _format_enum(self, enum):
        res = super()._format_enum(enum)

        return res

    def format_flags(self, flags):
        template = self.engine.get_template('gi_flags.html')
        out = template.render({'flags': flags})
        return out


# pylint: disable=too-many-instance-attributes
class GstExtension(Extension):
    extension_name = 'gst-extension'
    argument_prefix = 'gst'
    __dual_links = {}  # Maps myelement:XXX to GstMyElement:XXX
    __parsed_cfiles = set()
    __caches = {}  # cachefile -> dict
    __apps_sigs = set()
    __all_plugins_symbols = set()

    def __init__(self, app, project):
        super().__init__(app, project)
        self.cache = {}
        self.c_sources = []
        self.cache_file = None
        self.plugin = None
        self.__elements = {}
        self.__raw_comment_parser = GtkDocParser(
            project, section_file_matching=False)
        self.__plugins = None
        self.__toplevel_comments = OrderedSet()
        self.list_plugins_page = None
        # If we have a plugin with only one element, we render it on the plugin
        # page.
        self.unique_feature = None
        self.__on_index_symbols = []

    def _make_formatter(self):
        return GstFormatter(self)

    def create_symbol(self, *args, **kwargs):
        sym = super().create_symbol(*args, **kwargs)
        if self.unique_feature and sym:
            self.__on_index_symbols.append(sym)

        return sym

    # pylint: disable=too-many-branches
    def setup(self):
        # Make sure the cache file is save when the whole project
        # is done.
        if self.cache_file not in GstExtension.__apps_sigs and self.cache_file:
            GstExtension.__apps_sigs.add(self.cache_file)

        if not self.cache_file:
            if self.list_plugins_page:
                self.__plugins = self.create_symbol(
                    GstPluginsSymbol,
                    display_name="All " +
                    self.project.project_name.replace("-", " ").title(),
                    unique_name=self.project.project_name + "-all-gst-plugins",
                    plugins=[], all_plugins=True)

                super().setup()
            return

        comment_parser = GtkDocParser(self.project, False)
        to_parse_sources = set(self.c_sources) - GstExtension.__parsed_cfiles

        CCommentExtractor(self, comment_parser).parse_comments(
            to_parse_sources)
        GstExtension.__parsed_cfiles.update(self.c_sources)

        if not self.cache:
            error('setup-issue', "No cache loaded or created for %s" % self.plugin)

        plugins = []
        if self.plugin:
            pname = self.plugin
            dot_idx = pname.rfind('.')
            if dot_idx > 0:
                pname = self.plugin[:dot_idx]
            if pname.startswith('libgst'):
                pname = pname[6:]
            elif pname.startswith('gst'):
                pname = pname[3:]
            try:
                plugin_node = {pname: self.cache[pname]}
            except KeyError:
                error('setup-issue', "Plugin %s not found" % pname)
        else:
            plugin_node = self.cache

        for libfile, plugin in plugin_node.items():
            plugin_sym = self.__parse_plugin(libfile, plugin)
            if not plugin_sym:
                continue

            plugins.append(plugin_sym)

        if not self.plugin:
            self.__plugins = self.create_symbol(
                GstPluginsSymbol,
                display_name=self.project.project_name.replace(
                    "-", " ").title(),
                unique_name=self.project.project_name + "-gst-plugins",
                plugins=plugins)

        super().setup()

    def _get_comment_smart_key(self, comment):
        try:
            return comment.title.description
        except AttributeError:
            return None

    def _get_toplevel_comments(self):
        if self.unique_feature:
            return OrderedSet()
        return self.__toplevel_comments

    def get_plugin_comment(self):
        if self.plugin:
            res = self.app.database.get_comment("plugin-" + self.plugin)
            return res
        return None

    def make_pages(self):
        smart_pages = super().make_pages()

        if not self.__plugins:
            return None

        if self.list_plugins_page is None:
            index = smart_pages.get('gst-index')
            if index is None:
                return smart_pages

            index.render_subpages = False
            index.symbol_names.add(self.__plugins.unique_name)
            for sym in self.__on_index_symbols:
                index.symbol_names.add(sym.unique_name)
            if self.unique_feature:
                index.comment = self.app.database.get_comment("element-" + self.unique_feature)
            return smart_pages

        page = smart_pages.get(self.list_plugins_page)
        page.render_subpages = False
        page.extension_name = self.extension_name

        page.symbol_names.add(self.__plugins.unique_name)
        page.comment = self.get_plugin_comment()
        self.__plugins.plugins = self.__all_plugins_symbols

        return smart_pages

    def add_comment(self, comment):
        # We handle toplevel comments ourself, make sure all comments
        # end up in the database
        comment.toplevel = False

        super().add_comment(comment)

    def _get_smart_index_title(self):
        if self.plugin:
            return self.__plugins.display_name
        return 'GStreamer plugins documentation'

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('Gst extension', DESCRIPTION)
        GstExtension.add_index_argument(group)
        # GstExtension.add_order_generated_subpages(group)
        GstExtension.add_sources_argument(group, prefix='gst-c')
        group.add_argument('--gst-cache-file', default=None)
        group.add_argument('--gst-list-plugins-page', default=None)
        group.add_argument('--gst-plugin-name', default=None)
        group.add_argument('--gst-plugins-path', default=None)

    def parse_config(self, config):
        self.c_sources = config.get_sources('gst_c')
        self.cache_file = config.get('gst_cache_file')
        self.plugin = config.get('gst_plugin_name')
        self.list_plugins_page = config.get('gst_list_plugins_page', None)
        info('Parsing config!')

        self.cache = {}
        if self.cache_file:
            self.cache = GstExtension.__caches.get(self.cache_file)
            if not self.cache:
                try:
                    with open(self.cache_file) as _:
                        self.cache = json.load(_)
                except FileNotFoundError:
                    pass

                if self.cache is None:
                    self.cache = {}
                GstExtension.__caches[self.cache_file] = self.cache

        super().parse_config(config)

    def _get_smart_key(self, symbol):
        if self.unique_feature:
            return None

        if isinstance(symbol, GstPluginSymbol):
            # PluginSymbol are rendered on the index page
            return None
        res = symbol.extra.get('gst-element-name')
        if res:
            res = res.replace("element-", "")

        return res

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-arguments
    def __create_signal_symbol(self, obj, parent_uniquename, name, signal,
                               element_name, parent_name=None):
        atypes = signal['args']
        instance_type = obj['hierarchy'][0]
        unique_name = "%s::%s" % (parent_uniquename, name)
        aliases = self._get_aliases(["%s::%s" % (instance_type, name)])

        args_type_names = []
        args_type_names = [
            (type_tokens_from_type_name('GstElement'), 'param_0')]
        for i, _ in enumerate(atypes):
            args_type_names.append(
                (type_tokens_from_type_name(atypes[i]), 'param_%s' % (i + 1)))

        args_type_names.append(
            (type_tokens_from_type_name('gpointer'), "udata"))
        params = []

        for comment_name in [unique_name] + aliases:
            comment = self.app.database.get_comment(comment_name)
            if comment:
                for i, argname in enumerate(comment.params.keys()):
                    args_type_names[i] = (args_type_names[i][0], argname)

        for tokens, argname in args_type_names:
            params.append(ParameterSymbol(argname=argname, type_tokens=tokens))

        type_name = signal['retval']
        if type_name == 'void':
            retval = [None]
        else:
            tokens = type_tokens_from_type_name(type_name)

            enum = signal.get('return-values')
            if enum:
                self.__create_enum_symbol(
                    type_name, enum, obj.get('name', parent_uniquename),
                    parent_name=parent_name)

            retval = [ReturnItemSymbol(type_tokens=tokens)]

        return self.create_symbol(
            SignalSymbol, parameters=params, return_value=retval,
            display_name=name, unique_name=unique_name,
            extra={'gst-element-name': element_name},
            aliases=aliases, parent_name=parent_name)

    def __create_signal_symbols(self, obj, parent_uniquename, element_name,
                                parent_name=None):
        signals = obj.get('signals', {})
        if not signals:
            return

        for name, signal in signals.items():
            self.__create_signal_symbol(obj, parent_uniquename, name, signal,
                                        element_name, parent_name=parent_name)

    def __create_property_symbols(self, obj, parent_uniquename,
                                  pagename, parent_name=None):
        properties = obj.get('properties', [])
        if not properties:
            return

        for name, prop in properties.items():
            unique_name = '%s:%s' % (obj.get('name', parent_uniquename), name)
            flags = [ReadableFlag()]
            if prop['writable']:
                flags += [WritableFlag()]
            if prop['construct-only']:
                flags += [ConstructOnlyFlag()]
            elif prop['construct']:
                flags += [ConstructFlag()]

            type_name = prop['type-name']

            tokens = type_tokens_from_type_name(type_name)
            type_ = QualifiedSymbol(type_tokens=tokens)

            default = prop.get('default')
            enum = prop.get('values')
            if enum:
                type_ = self.__create_enum_symbol(
                    prop['type-name'], enum, obj.get('name', parent_uniquename),
                    parent_name=parent_name)

            if obj['hierarchy'][0] != parent_uniquename:
                aliases = self._get_aliases(['%s:%s' % (obj['hierarchy'][0], name)])
            else:
                aliases = []

            res = self.app.database.get_symbol(unique_name)
            if res is None:
                res = self.create_symbol(
                    PropertySymbol,
                    prop_type=type_,
                    display_name=name, unique_name=unique_name,
                    aliases=aliases, parent_name=parent_name,
                    extra={'gst-element-name': pagename},
                )
            assert res

            if not self.app.database.get_comment(unique_name):
                comment = Comment(unique_name, Comment(name=name),
                                  description=prop['blurb'])
                self.app.database.add_comment(comment)

            # FIXME This is incorrect, it's not yet format time (from gi_extension)
            extra_content = self.formatter.format_flags(flags)
            res.extension_contents['Flags'] = extra_content
            if default:
                res.extension_contents['Default value'] = default

    def __create_enum_symbol(self, type_name, enum, element_name, parent_name=None):
        display_name = re.sub(
            r"([a-z])([A-Z])", r"\g<1>-\g<2>", type_name.replace('Gst', ''))
        unique_name = type_name
        if self.app.database.get_symbol(unique_name):
            unique_name = element_name + '_' + type_name
        symbol = self.app.database.get_symbol(unique_name)
        if not symbol:
            members = []
            for val in enum:
                value_unique_name = "%s::%s" % (type_name, val['name'])
                if self.app.database.get_symbol(value_unique_name):
                    value_unique_name = "%s::%s" % (
                        element_name + '_' + type_name, val['name'])
                member_sym = self.create_symbol(GstNamedConstantValue,
                                                unique_name=value_unique_name,
                                                display_name=val['name'],
                                                value=val['value'],
                                                parent_name=parent_name, val=val,
                                                extra={'gst-element-name': element_name})
                if member_sym:
                    members.append(member_sym)
            symbol = self.create_symbol(
                GstNamedConstantsSymbols, anonymous=False,
                raw_text=None, display_name=display_name.capitalize(),
                unique_name=unique_name, parent_name=parent_name,
                members=members,
                extra={'gst-element-name': 'element-' + element_name})
        elif not isinstance(symbol, GstNamedConstantsSymbols):
            self.warn('symbol-redefined', "EnumMemberSymbol(unique_name=%s, project=%s)"
                      " has already been defined: %s" % (unique_name, self.project.project_name,
                                                         symbol))

            return None

        if not symbol:
            return None

        symbol.values = enum
        return symbol

    def __create_object_type(self, element, _object):
        if not _object:
            return None

        unique_name = _object['hierarchy'][0]
        if self.app.database.get_symbol(unique_name):
            return None

        pagename = 'element-' + element['name']
        self.__create_property_symbols(_object, unique_name, pagename, parent_name=unique_name)
        self.__create_signal_symbols(_object, unique_name, pagename, parent_name=unique_name)

        return self.create_symbol(
            ClassSymbol,
            hierarchy=create_hierarchy(_object),
            display_name=unique_name,
            unique_name=unique_name,
            parent_name=unique_name,
            extra={'gst-element-name': pagename}
        )

    def __create_pad_template_symbols(self, element, plugin_name):
        templates = element.get('pad-templates', {})
        if not templates:
            return

        for tname, template in templates.items():
            name = tname.replace("%%", "%")
            unique_name = '%s->%s' % (element['hierarchy'][0], name)
            object_type = self.__create_object_type(element, template.get("object-type"))
            self.create_symbol(GstPadTemplateSymbol,
                               name=name,
                               direction=template["direction"],
                               presence=template["presence"],
                               caps=template["caps"],
                               filename=plugin_name, parent_name=None,
                               object_type=object_type,
                               display_name=name, unique_name=unique_name,
                               extra={'gst-element-name': 'element-' + element['name']})

    def _get_aliases(self, aliases):
        return [alias for alias in aliases if not self.app.database.get_symbol(alias)]

    def __parse_plugin(self, plugin_name, plugin):
        elements = []
        if self.plugin and len(plugin.get('elements', {}).items()) == 1:
            self.unique_feature = list(plugin.get('elements', {}).keys())[0]

        for ename, element in plugin.get('elements', {}).items():
            comment = None
            element['name'] = ename

            pagename = 'element-' + element['name']
            for comment_name in [pagename, element['name'], element['hierarchy'][0]]:
                comment = self.app.database.get_comment(comment_name)
                if comment:
                    break

            if not comment:
                comment = Comment(
                    pagename,
                    Comment(description=element['name']),
                    description=element['description'],
                    short_description=Comment(description=element['description']))
                self.app.database.add_comment(comment)
            elif not comment.short_description:
                comment.short_description = Comment(
                    description=element['description'])
            comment.title = Comment(description=element['name'])
            comment.name = element['name']
            comment.meta['title'] = element['name']
            self.__toplevel_comments.add(comment)

            aliases = self._get_aliases([pagename, element['hierarchy'][0]])
            sym = self.create_symbol(
                GstElementSymbol,
                parent_name=None,
                display_name=element['name'],
                hierarchy=create_hierarchy(element),
                unique_name=element['name'],
                filename=plugin_name,
                extra={'gst-element-name': pagename},
                rank=str(element['rank']), author=element['author'],
                classification=element['klass'], plugin=plugin['filename'],
                aliases=aliases,
                package=plugin['package'])

            if not sym:
                continue

            self.__elements[element['name']] = sym
            self.__create_property_symbols(element, element['name'], pagename)
            self.__create_signal_symbols(element, element['name'], pagename)
            self.__create_pad_template_symbols(element, plugin_name)

            elements.append(sym)

        plugin = self.create_symbol(
            GstPluginSymbol,
            description=plugin['description'],
            display_name=plugin_name,
            unique_name='plugin-' + plugin['filename'],
            license=plugin['license'],
            package=plugin['package'],
            filename=plugin['filename'],
            elements=elements,
            extra={'gst-plugins': 'plugins-' + plugin['filename']})

        if not plugin:
            return None

        self.__all_plugins_symbols.add(plugin)

        if self.plugin:
            self.__plugins = plugin
        return plugin

    def __get_link_cb(self, resolver, name):
        link = self.__dual_links.get(name)
        if link:
            # Upsert link on the first run
            if isinstance(link, str):
                sym = self.app.database.get_symbol(link)
                link = sym.link

        if link:
            return link

        return (resolver, name)

    def format_page(self, page, link_resolver, output):
        link_resolver.get_link_signal.connect(GIExtension.search_online_links)
        super().format_page(page, link_resolver, output)
        link_resolver.get_link_signal.disconnect(
            GIExtension.search_online_links)
