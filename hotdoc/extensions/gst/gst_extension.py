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

# pylint: disable=too-many-lines

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
from hotdoc.extensions.gi.languages import CLanguage
from hotdoc.core.links import Link
from hotdoc.utils.loggable import info, error
from hotdoc.utils.utils import OrderedSet
from hotdoc.core.extension import Extension
from hotdoc.core.symbols import ClassSymbol, QualifiedSymbol, PropertySymbol, \
    SignalSymbol, ReturnItemSymbol, ParameterSymbol, Symbol, InterfaceSymbol
from hotdoc.parsers.gtk_doc import GtkDocParser, gather_links, search_online_links
from hotdoc.extensions.c.utils import CCommentExtractor
from hotdoc.core.formatter import Formatter
from hotdoc.core.comment import Comment
from hotdoc.extensions.gi.gi_extension import WritableFlag, ReadableFlag, \
    ConstructFlag, ConstructOnlyFlag
from hotdoc.extensions.gi.symbols import GIClassSymbol, GIInterfaceSymbol
from hotdoc.extensions.devhelp.devhelp_extension import TYPE_MAP


DESCRIPTION =\
    """
Extract gstreamer plugin documentation from sources and
built plugins.
"""


def _inject_fundamentals():
    # Working around https://gitlab.freedesktop.org/gstreamer/gst-plugins-good/-/issues/744
    CLanguage.add_fundamental("JackClient", Link("https://jackaudio.org/api/jack_8h.html",
                                                 'jack_client_t', None))
    CLanguage.add_fundamental(
        "GrapheneMatrix",
        Link("https://developer.gnome.org/graphene/stable/graphene-Matrix.html#graphene-matrix-t",
             'graphen_matrix_t', 'GrapheneMatrix'))
    CLanguage.add_fundamental(
        "CairoContext",
        Link("https://www.cairographics.org/manual/cairo-cairo-t.html#cairo-t",
             'cairo_t', 'CairoContext'))


def _cleanup_package_name(package_name):
    return package_name.strip(
        'git').strip('release').strip(
            'prerelease').strip(
                'GStreamer').strip(
                    'Plug-ins').strip(' ')


def type_tokens_from_type_name(type_name, python_lang):
    res = [Link(None, type_name, type_name, mandatory=True)]
    if python_lang and not python_lang.get_fundamental(type_name):
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
        return list(self.plugins) + super().get_children_symbols()

    @classmethod
    def get_plural_name(cls):
        return ""


class GstElementSymbol(GIClassSymbol):
    TEMPLATE = """
        @require(symbol, hierarchy, desc, interfaces)
        @desc

        @if hierarchy:
        <h2>Hierarchy</h2>
            <div class="hierarchy_container">
                @hierarchy
            </div>
        @end
        @if interfaces:
            <h2>Implemented interfaces</h2>
            <div>
                <pre>
                @for interface in interfaces:
@interface
 \
@end
</pre>
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
        self.pad_templates = []
        super().__init__(**kwargs)

    @classmethod
    def get_plural_name(cls):
        return ""

    def get_children_symbols(self):
        return super().get_children_symbols() + self.pad_templates


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
        self.other_types = []
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return super().get_children_symbols() + self.elements + self.other_types

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
        return self.members + super().get_children_symbols()

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
            @symbol.formatted_doc
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
        self.object_type = None
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return [self.qtype, self.object_type] + super().get_children_symbols()

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
        self._ordering.insert(self._ordering.index(ClassSymbol) + 1, GIClassSymbol)
        self._ordering.insert(self._ordering.index(GIClassSymbol) + 1, GstPadTemplateSymbol)
        self._ordering.insert(self._ordering.index(GstPadTemplateSymbol) + 1, GstPluginsSymbol)
        self._ordering.insert(self._ordering.index(InterfaceSymbol) + 1, GIInterfaceSymbol)
        self._ordering.append(GstNamedConstantsSymbols)

        self._symbol_formatters.update(
            {GstPluginsSymbol: self._format_plugins_symbol,
             GstPluginSymbol: self._format_plugin_symbol,
             GstPadTemplateSymbol: self._format_pad_template_symbol,
             GstElementSymbol: self._format_element_symbol,
             GstNamedConstantsSymbols: self._format_enum,
             GIClassSymbol: self._format_class_symbol,
             GIInterfaceSymbol: self._format_interface_symbol,
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
        if None in page.by_parent_symbols:
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
        symbol.object_type.rendered_link = self._format_linked_symbol(symbol.object_type)
        return template.render({'symbol': symbol})

    def _format_element_symbol(self, symbol):
        hierarchy = self._format_hierarchy(symbol)

        template = self.engine.get_template('element.html')
        interfaces = []
        for interface in symbol.interfaces:
            interfaces.append(self._format_linked_symbol(interface))
        return template.render({'symbol': symbol, 'hierarchy': hierarchy, 'desc': '',
                                'interfaces': interfaces})

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

        # Links GTypeName to pagename for other-types so we now where to locate
        # the symbols on creation.
        self.__other_types_pages = {}

    def _make_formatter(self):
        return GstFormatter(self)

    def create_symbol(self, *args, **kwargs):
        sym = super().create_symbol(*args, **kwargs)
        if self.unique_feature and sym:
            self.__on_index_symbols.append(sym)

        return sym

    # pylint: disable=too-many-branches
    def setup(self):
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

        gather_links()

        comment_parser = GtkDocParser(self.project, False)
        to_parse_sources = set(self.c_sources) - GstExtension.__parsed_cfiles

        CCommentExtractor(self, comment_parser).parse_comments(
            to_parse_sources)
        GstExtension.__parsed_cfiles.update(self.c_sources)

        self.debug("Parsing plugin %s, (cache file %s)" % (self.plugin, self.cache_file))

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
            else:
                index.comment = self.get_plugin_comment()
            return smart_pages

        page = smart_pages.get(self.list_plugins_page)
        page.render_subpages = False
        page.extension_name = self.extension_name

        page.symbol_names.add(self.__plugins.unique_name)
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

    def __create_symbol(self, gtype, symbol, pagename):
        if symbol["kind"] in ["enum", "flags"]:
            if pagename in self.__other_types_pages:
                # The enum was defined by another type (not an element)
                # this page will be rendered as any GObject so we need
                # to specify its parent name
                parent_name = pagename
            else:
                parent_name = None
            return self.__create_enum_symbol(gtype, symbol.get('values'), pagename,
                                             parent_name=parent_name)
        if symbol["kind"] == "object":
            return self.__create_classed_type(gtype, symbol)
        if symbol["kind"] == "interface":
            return self.__create_classed_type(gtype, symbol, True)

        assert "Not reached" == "False"
        return None

    def _remember_symbol_type(self, gtype, pagename):
        self.__other_types_pages[gtype] = pagename

        return gtype

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-arguments
    def __create_signal_symbol(self, obj, parent_uniquename, name, signal,
                               pagename, parent_name=None):
        args = signal['args']
        instance_type = obj['hierarchy'][0]
        unique_name = "%s::%s" % (parent_uniquename, name)
        aliases = ["%s::%s" % (instance_type, name)]

        gi_extension = self.project.extensions.get('gi-extension')
        python_lang = gi_extension.get_language('python')
        args_type_names = [(type_tokens_from_type_name('GstElement', python_lang), 'param_0')]
        for arg in args:
            arg_name = arg["name"]
            arg_type_name = self._remember_symbol_type(arg["type"], pagename)
            type_tokens = type_tokens_from_type_name(arg_type_name, python_lang)
            args_type_names.append((type_tokens, arg_name))

        args_type_names.append(
            (type_tokens_from_type_name('gpointer', python_lang), "udata"))
        params = []

        for comment_name in [unique_name] + aliases:
            comment = self.app.database.get_comment(comment_name)
            if comment:
                for i, argname in enumerate(comment.params.keys()):
                    args_type_names[i] = (args_type_names[i][0], argname)

        for tokens, argname in args_type_names:
            params.append(ParameterSymbol(argname=argname, type_tokens=tokens))

        return_type_name = self._remember_symbol_type(
            signal["return-type"], pagename)
        if return_type_name == 'void':
            retval = [None]
        else:
            tokens = type_tokens_from_type_name(return_type_name, python_lang)
            retval = [ReturnItemSymbol(type_tokens=tokens)]

        res = self.create_symbol(
            SignalSymbol, parameters=params, return_value=retval,
            display_name=name, unique_name=unique_name,
            extra={'gst-element-name': pagename},
            aliases=aliases, parent_name=parent_name)

        if res:
            flags = []

            when = signal.get('when')
            if when == "first":
                flags.append(gi.flags.RunFirstFlag())
            elif when == "last":
                flags.append(gi.flags.RunLastFlag())
            elif when == "cleanup":
                flags.append(gi.flags.RunCleanupFlag())

            no_hooks = signal.get('no-hooks')
            if no_hooks:
                flags.append(gi.flags.NoHooksFlag())

            action = signal.get('action')
            if action:
                flags.append(gi.flags.ActionFlag())

            # This is incorrect, it's not yet format time
            extra_content = self.formatter.format_flags(flags)
            res.extension_contents['Flags'] = extra_content

        return res

    def __create_signal_symbols(self, obj, parent_uniquename, element_name,
                                parent_name=None):
        res = []
        signals = obj.get('signals', {})
        if not signals:
            return res

        for name, signal in signals.items():
            res.append(self.__create_signal_symbol(
                obj, parent_uniquename, name, signal,
                element_name,
                parent_name=parent_name))
        return res

    def __create_property_symbols(self, obj, parent_uniquename,
                                  pagename, parent_name=None):
        res = []
        properties = obj.get('properties', [])
        if not properties:
            return res

        gi_extension = self.project.extensions.get('gi-extension')
        python_lang = gi_extension.get_language('python')
        for name, prop in properties.items():
            unique_name = '%s:%s' % (obj.get('name', parent_uniquename), name)
            flags = [ReadableFlag()]
            if prop['writable']:
                flags += [WritableFlag()]
            if prop['construct-only']:
                flags += [ConstructOnlyFlag()]
            elif prop['construct']:
                flags += [ConstructFlag()]

            prop_type_name = self._remember_symbol_type(
                prop["type"], pagename)

            tokens = type_tokens_from_type_name(prop_type_name, python_lang)
            type_ = QualifiedSymbol(type_tokens=tokens)

            default = prop.get('default')
            if obj['hierarchy'][0] != parent_uniquename:
                aliases = ['%s:%s' % (obj['hierarchy'][0], name)]
            else:
                aliases = []

            sym = self.app.database.get_symbol(unique_name)
            if sym is None:
                sym = self.create_symbol(
                    PropertySymbol,
                    prop_type=type_,
                    display_name=name, unique_name=unique_name,
                    aliases=aliases, parent_name=parent_name,
                    extra={'gst-element-name': pagename},
                )
            assert sym

            if not self.app.database.get_comment(unique_name):
                comment = Comment(unique_name, Comment(name=name),
                                  description=prop['blurb'])
                self.app.database.add_comment(comment)

            # FIXME This is incorrect, it's not yet format time (from gi_extension)
            extra_content = self.formatter.format_flags(flags)
            sym.extension_contents['Flags'] = extra_content
            if default:
                if prop_type_name in ['GstCaps', 'GstStructure']:
                    default = '<pre class="language-yaml">' + \
                        '<code class="language-yaml">%s</code></pre>' % default
                sym.extension_contents['Default value'] = default
            res.append(sym)

        return res

    def __create_enum_symbol(self, type_name, enum, pagename, parent_name=None):
        display_name = re.sub(
            r"([a-z])([A-Z])", r"\g<1>-\g<2>", type_name.replace('Gst', ''))

        unique_name = type_name
        if self.app.database.get_symbol(unique_name):
            # Still required as some bin manually proxy children properties inside
            # themselves (like GstFakeSinkStateError in fakevideosink for example)
            unique_name = pagename + '_' + type_name
        members = []
        for val in enum:
            value_unique_name = "%s::%s" % (type_name, val['name'])
            if self.app.database.get_symbol(value_unique_name):
                value_unique_name = "%s_%s" % (pagename, value_unique_name)
            member_sym = self.create_symbol(GstNamedConstantValue,
                                            unique_name=value_unique_name,
                                            display_name=val['name'],
                                            value=val['value'],
                                            parent_name=parent_name, val=val,
                                            extra={'gst-element-name': pagename})
            if member_sym:
                members.append(member_sym)

        symbol = self.create_symbol(
            GstNamedConstantsSymbols, anonymous=False,
            raw_text=None, display_name=display_name.capitalize(),
            unique_name=unique_name, parent_name=parent_name,
            members=members,
            extra={'gst-element-name': pagename})

        if not symbol:
            return None

        symbol.values = enum
        return symbol

    def __create_hierarchy(self, pagename, element_dict):
        hierarchy = []
        for klass_name in element_dict["hierarchy"][1:]:
            self._remember_symbol_type(klass_name, pagename)
            link = Link(None, klass_name, klass_name, mandatory=True)
            sym = QualifiedSymbol(type_tokens=[link])
            hierarchy.append(sym)

        hierarchy.reverse()
        return hierarchy

    def __create_classed_type(self, pagename, _object, is_interface=False):
        unique_name = _object['hierarchy'][0]
        properties = self.__create_property_symbols(
            _object, unique_name, pagename, parent_name=unique_name)
        signals = self.__create_signal_symbols(
            _object, unique_name, pagename, parent_name=unique_name)

        return self.create_symbol(
            GIInterfaceSymbol if is_interface else GIClassSymbol,
            hierarchy=self.__create_hierarchy(pagename, _object),
            display_name=unique_name,
            unique_name=unique_name,
            parent_name=unique_name,
            properties=properties,
            signals=signals,
            extra={'gst-element-name': pagename}
        )

    def __create_pad_template_symbols(self, element, plugin_name):
        templates = element.get('pad-templates', {})
        res = []
        if not templates:
            return res

        for tname, template in templates.items():
            name = tname.replace("%%", "%")
            unique_name = '%s!%s' % (element['hierarchy'][0], name)
            pagename = 'element-' + element['name']
            gtype = self._remember_symbol_type(template.get("type", "GstPad"), pagename)
            link = Link(None, gtype, gtype, mandatory=True)
            object_type = QualifiedSymbol(type_tokens=[link])
            res.append(self.create_symbol(
                GstPadTemplateSymbol,
                name=name,
                direction=template["direction"],
                presence=template["presence"],
                caps=template["caps"],
                filename=plugin_name, parent_name=None,
                object_type=object_type,
                display_name=name, unique_name=unique_name,
                extra={'gst-element-name': pagename}))

        return res

    def __extract_feature_comment(self, feature_type, feature):
        pagename = feature_type + '-' + feature['name']
        possible_comment_names = [pagename, feature['name']]
        if feature_type == 'element':
            possible_comment_names.append(feature['hierarchy'][0])

        comment = None
        for comment_name in possible_comment_names:
            comment = self.app.database.get_comment(comment_name)
            if comment:
                break

        description = feature.get('description')
        if not comment:
            comment = Comment(
                pagename,
                Comment(description=feature['name']),
                description=description,
                short_description=Comment(description=description))
            self.app.database.add_comment(comment)
        elif not comment.short_description:
            comment.short_description = Comment(
                description=description)
        comment.title = Comment(description=feature['name'])
        comment.name = feature.get('name', pagename)
        comment.meta['title'] = feature['name']
        self.__toplevel_comments.add(comment)

        return pagename, comment

    def __parse_plugin(self, plugin_name, plugin):
        elements = []
        feature_names = list(plugin.get('elements', {}).keys()) \
            + list(plugin.get('tracers', {}).keys()) \
            + list(plugin.get('device-providers', {}).keys())

        self.__other_types_pages = {}
        if self.plugin and len(feature_names) == 1:
            self.unique_feature = feature_names[0]

        for ename, tracer in plugin.get('tracers', {}).items():
            tracer['name'] = ename
            self.__extract_feature_comment("tracer", tracer)

        other_types = []
        for provider_name, provider in plugin.get('device-providers', {}).items():
            provider['name'] = provider_name
            _, comment = self.__extract_feature_comment("provider", provider)
            comment.description += """\n\n# Provided device example"""
            other_types.append(self.__create_classed_type(provider_name,
                                                          provider.get('device-example')))

        for ename, element in plugin.get('elements', {}).items():
            element['name'] = ename
            pagename, _ = self.__extract_feature_comment("element", element)
            interfaces = []
            for interface in element.get("interfaces", []):
                self._remember_symbol_type(interface, pagename)
                interfaces.append(QualifiedSymbol(
                    type_tokens=[Link(None, interface, interface, mandatory=True)]))

            aliases = [pagename, element['hierarchy'][0]]
            sym = self.create_symbol(
                GstElementSymbol,
                parent_name=None,
                display_name=element['name'],
                hierarchy=self.__create_hierarchy(pagename, element),
                unique_name=element['name'],
                filename=plugin_name,
                extra={'gst-element-name': pagename},
                rank=str(element['rank']), author=element['author'],
                classification=element['klass'],
                plugin=plugin_name,
                aliases=aliases,
                package=plugin['package'],
                interfaces=interfaces)

            if not sym:
                continue

            self.__elements[element['name']] = sym
            sym.properties.extend(self.__create_property_symbols(
                element, element['name'], pagename))
            sym.signals.extend(self.__create_signal_symbols(element, element['name'], pagename))
            sym.pad_templates.extend(self.__create_pad_template_symbols(element, plugin_name))

            elements.append(sym)

        types = list(plugin['other-types'].items())
        while True:
            type_ = None
            for tmptype in types:
                if tmptype[0] in self.__other_types_pages:
                    type_ = tmptype
                    break

            if not type_:
                break

            types.remove(type_)
            other_types.append(self.__create_symbol(
                type_[0], type_[1], self.__other_types_pages[type_[0]]))

        for _type in types:
            self.warn("no-location-indication",
                      "Type %s has been marked with `gst_type_mark_as_plugin_api`"
                      " but is not used in any of %s API (it might require to"
                      " be manually removed from the cache in case of plugin"
                      " move)" % (_type[0], plugin_name))

        plugin = self.create_symbol(
            GstPluginSymbol,
            description=plugin['description'],
            display_name=plugin_name,
            unique_name='plugin-' + plugin_name,
            license=plugin['license'],
            package=plugin['package'],
            filename=plugin['filename'],
            elements=elements,
            other_types=other_types,
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
        link_resolver.get_link_signal.connect(search_online_links)
        super().format_page(page, link_resolver, output)
        link_resolver.get_link_signal.disconnect(
            search_online_links)


TYPE_MAP.update({GstElementSymbol: 'class', GstNamedConstantsSymbols: 'enum'})
_inject_fundamentals()
