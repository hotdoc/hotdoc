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

# pylint: disable=too-many-lines

"""
The base formatter module.

By design, hotdoc only supports html output.
"""

import os
import html
import re
import json
import urllib.parse
from urllib.request import urlretrieve
import shutil
import tarfile
import hashlib

from collections import namedtuple

import appdirs

from lxml import etree

# pylint: disable=import-error
from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.ext.code import CodeExtension
from wheezy.template.loader import FileLoader

# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import
from hotdoc.core.symbols import *
from hotdoc.core.links import Link
from hotdoc.parsers.gtk_doc import GtkDocStringFormatter
from hotdoc.utils.utils import (
    OrderedSet, id_from_text, recursive_overwrite)
from hotdoc.core.exceptions import HotdocException
from hotdoc.utils.loggable import Logger, warn, debug
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.signals import Signal


class FormatterBadLinkException(HotdocException):
    """
    Raised when a produced html page contains an empty local link
    to nowhere.
    """
    pass


XSLT_PAGE_TRANSFORM = etree.XML('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:hotdoc="uri:hotdoc">
    <xsl:variable name="subpages" select="hotdoc:subpages()" />
    <xsl:template match="subpages">
        <xsl:apply-templates select="$subpages" />
    </xsl:template>
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
</xsl:stylesheet>''')


Logger.register_warning_code('bad-local-link', FormatterBadLinkException,
                             domain='html-formatter')
Logger.register_warning_code('no-image-src', FormatterBadLinkException,
                             domain='html-formatter')
Logger.register_warning_code('bad-image-src', FormatterBadLinkException,
                             domain='html-formatter')
Logger.register_warning_code('download-theme-error', HotdocException,
                             domain='html-formatter')


HERE = os.path.dirname(__file__)


def _download_progress_cb(blocknum, blocksize, totalsize):
    """Banana Banana"""
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        msg = "\r%5.1f%% %*d / %d" % (
            percent, len(str(totalsize)), readsofar, totalsize)
        print(msg)
        if readsofar >= totalsize:  # near the end
            print("\n")
    else:  # total size is unknown
        print("read %d\n" % (readsofar,))


# pylint: disable=too-few-public-methods
class TocSection:
    """
    Banana banana
    """

    def __init__(self, summaries, name):
        self.summaries = summaries
        self.name = name
        self.id_ = ''.join(name.split())


# pylint: disable=too-few-public-methods
class SymbolDescriptions:
    """
    Banana banana
    """

    def __init__(self, descriptions, name):
        self.descriptions = descriptions
        self.name = name


# pylint: disable=too-many-instance-attributes
class Formatter(Configurable):
    """
    Takes care of rendering the documentation symbols and comments into HTML
    pages.
    """
    theme_path = None
    theme_meta = {}
    extra_theme_path = None
    add_anchors = False
    number_headings = False
    engine = None
    ext_engine = None
    all_scripts = set()
    all_stylesheets = set()
    get_extra_files_signal = Signal()
    initialized = False

    def __init__(self, extension):
        """
        Args:
            extension (`extension.Extension`): The extension instance.
        """
        Configurable.__init__(self)

        self.extension = extension

        self._symbol_formatters = {
            FunctionSymbol: self._format_function,
            ConstructorSymbol: self._format_function,
            MethodSymbol: self._format_function,
            ClassMethodSymbol: self._format_function,
            ClassSymbol: self._format_function,
            FunctionMacroSymbol: self._format_function_macro,
            CallbackSymbol: self._format_callback,
            ConstantSymbol: self._format_constant,
            ExportedVariableSymbol: self._format_constant,
            AliasSymbol: self._format_alias,
            StructSymbol: self._format_struct,
            EnumSymbol: self._format_enum,
            EnumMemberSymbol: self._format_enum_member_symbol,
            ParameterSymbol: self._format_parameter_symbol,
            ReturnItemSymbol: self._format_return_item_symbol,
            FieldSymbol: self._format_field_symbol,
            SignalSymbol: self._format_signal_symbol,
            VFunctionSymbol: self._format_vfunction_symbol,
            PropertySymbol: self._format_property_symbol,
            ClassSymbol: self._format_class_symbol,
            InterfaceSymbol: self._format_interface_symbol,
        }

        self._ordering = [InterfaceSymbol, ClassSymbol, ConstructorSymbol,
                          MethodSymbol, ClassMethodSymbol, FunctionSymbol,
                          FunctionMacroSymbol, SignalSymbol, PropertySymbol,
                          StructSymbol, VFunctionSymbol, EnumSymbol,
                          ConstantSymbol, ExportedVariableSymbol, AliasSymbol,
                          CallbackSymbol]

        self._docstring_formatter = self._make_docstring_formatter()
        self._current_page = None
        self.extra_assets = None
        self.add_anchors = False
        self.number_headings = False
        self.writing_page_signal = Signal()
        self.formatting_page_signal = Signal()
        self.formatting_symbol_signal = Signal()
        self._order_by_parent = False

        self.__cache_dir = os.path.join(self.extension.app.private_folder,
                                        'cache')
        self.__page_transform = etree.XSLT(XSLT_PAGE_TRANSFORM)

    def _make_docstring_formatter(self):  # pylint: disable=no-self-use
        return GtkDocStringFormatter()

    # pylint: disable=no-self-use
    def _get_assets_path(self):
        """
        Banana banana
        """
        return 'assets'

    # pylint: disable=unused-argument
    def format_symbol(self, symbol, link_resolver):
        """
        Format a symbols.Symbol
        """
        if not symbol:
            return ''

        if isinstance(symbol, FieldSymbol):
            return ''

        # pylint: disable=unused-variable
        out = self._format_symbol(symbol)
        template = self.get_template('symbol_wrapper.html')

        return template.render(
            {'symbol': symbol,
             'formatted_doc': out})

    # pylint: disable=too-many-function-args
    def format_comment(self, comment, link_resolver):
        """Format a comment

        Args:
            comment: hotdoc.core.comment.Comment, the code comment
            to format. Can be None, in which case the empty string will
            be returned.
        Returns:
            str: The formatted comment.
        """
        if comment:
            return self._format_comment(comment, link_resolver)
        return ''

    def __copy_extra_assets(self, output):
        paths = []
        for src in self.extra_assets or []:
            dest = os.path.join(output, os.path.basename(src))

            destdir = os.path.dirname(dest)
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            if os.path.isdir(src):
                recursive_overwrite(src, dest)
            elif os.path.isfile(src):
                shutil.copyfile(src, dest)
            paths.append(dest)

        return paths

    def copy_assets(self, assets_path):
        """Banana banana
        """
        if not os.path.exists(assets_path):
            os.mkdir(assets_path)

        extra_files = self._get_extra_files()

        for ex_files in Formatter.get_extra_files_signal(self):
            extra_files.extend(ex_files)

        for src, dest in extra_files:
            dest = os.path.join(assets_path, dest)

            destdir = os.path.dirname(dest)
            if not os.path.exists(destdir):
                os.makedirs(destdir)
            if os.path.isfile(src):
                shutil.copy(src, dest)
            elif os.path.isdir(src):
                recursive_overwrite(src, dest)

    def format_page(self, page):
        """
        Banana banana
        """
        self.formatting_page_signal(self, page)
        return self._format_page(page)

    # pylint: disable=no-self-use
    def __load_theme_templates(self, searchpath, path):
        theme_templates_path = os.path.join(path, 'templates')

        if os.path.exists(theme_templates_path):
            searchpath.insert(0, theme_templates_path)

    # pylint: disable=no-self-use
    def __init_section_numbers(self, root):
        if not Formatter.number_headings:
            return {}

        targets = []

        ctr = 0
        while len(targets) <= 1:
            ctr += 1
            if ctr > 5:
                return {}

            targets = root.xpath('.//*[self::h%s]' % ctr)

        section_numbers = {}
        for i in range(ctr, 6):
            section_numbers['h%d' % i] = 0

        section_numbers['first'] = ctr

        return section_numbers

    # pylint: disable=no-self-use
    def __update_section_number(self, target, section_numbers):
        if not Formatter.number_headings or target.tag not in section_numbers:
            return None

        prev = section_numbers.get('prev')
        cur = int(target.tag[1])

        if cur < prev:
            for i in range(cur + 1, 6):
                section_numbers['h%d' % i] = 0

        section_numbers[target.tag] += 1
        section_numbers['prev'] = cur

        section_number = u''
        for i in range(section_numbers['first'], cur + 1):
            if section_number:
                section_number += '.'
            section_number += str(section_numbers['h%d' % i])

        return section_number

    def _make_title_id(self, node, id_nodes):
        if node.tag == 'img':
            text = node.attrib.get('alt')
        else:
            text = "".join([x for x in node.itertext()])

        if not text:
            return None

        id_ = id_from_text(text)
        ref_id = id_
        index = 1

        while id_ in id_nodes:
            id_ = '%s%s' % (ref_id, index)
            index += 1

        return id_

    def __update_targets(self, doc_root, section_numbers, id_nodes):
        targets = doc_root.xpath(
            './/*[@data-hotdoc-role="main"]//*[self::h1 or self::h2 or '
            'self::h3 or self::h4 or self::h5 or self::img]')

        for target in targets:
            if 'id' in target.attrib:
                continue

            id_ = self._make_title_id(target, id_nodes)

            section_number = self.__update_section_number(
                target, section_numbers)

            if section_number:
                target.text = '%s %s' % (section_number, target.text or '')

            if id_ is None:
                continue

            target.attrib['id'] = id_
            id_nodes[id_] = target

    def __update_links(self, page, doc_root, id_nodes):
        rel_path = os.path.join(self.get_output_folder(page), page.link.ref)
        links = doc_root.xpath('.//*[@data-hotdoc-role="main"]//a')
        for link in links:
            href = link.attrib.get('href')
            if href and href.startswith('#'):
                if not link.text and not link.getchildren():
                    id_node = id_nodes.get(href.strip('#'))
                    if id_node is not None:
                        link.text = ''.join([x for x in id_node.itertext()])
                    else:
                        warn('bad-local-link',
                             "Empty anchor link to %s in %s points nowhere" %
                             (href, page.name))
                        link.text = "FIXME broken link to %s" % href
                link.attrib["href"] = rel_path + href

    def __validate_html(self, project, page, doc_root):
        id_nodes = {n.attrib['id']: n for n in doc_root.xpath('.//*[@id]')}

        section_numbers = self.__init_section_numbers(doc_root)

        self.__update_targets(doc_root, section_numbers, id_nodes)

        self.__update_links(page, doc_root, id_nodes)

        assets = doc_root.xpath('.//*[@data-hotdoc-role="main"]//*[@src]')
        # All required assets should now be in place
        for asset in assets:
            self.__lookup_asset(asset, project, page)

    def __lookup_asset(self, asset, project, page):
        src = asset.attrib.get('src')
        if not src:
            warn('no-image-src',
                 'Empty image source in %s' % page.name)
            return

        comps = urllib.parse.urlparse(src)
        if comps.scheme:
            return

        folders = [os.path.dirname(page.source_file)] if not page.generated \
            else []
        folders += [os.path.join(folder, os.path.pardir)
                    for folder in project.extra_asset_folders]

        for folder in folders:
            path = os.path.abspath(os.path.join(folder, src))
            if os.path.exists(path):
                output_folder = os.path.join(
                    self.get_output_folder(page),
                    os.path.dirname(page.link.ref))
                project.extra_assets[os.path.join(output_folder, src)] = path
                asset.attrib['src'] = os.path.join(output_folder, src)
                return

        warn('bad-image-src',
             ('In %s, a local assets refers to an unknown source (%s). '
              'It should be available in one of these locations: %s') %
             (page.name, src, str(folders)))

    def write_out(self, page, xml_subpages, output):
        """Banana banana
        """
        # pylint: disable=missing-docstring
        def subpages(_):
            return xml_subpages

        namespace = etree.FunctionNamespace('uri:hotdoc')
        namespace['subpages'] = subpages
        html_output = os.path.join(output, 'html')

        rel_path = os.path.join(self.get_output_folder(page), page.link.ref)
        cached_path = os.path.join(self.__cache_dir, rel_path)
        full_path = os.path.join(html_output, rel_path)

        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))
        with open(cached_path, 'r', encoding='utf-8') as _:
            doc_root = etree.HTML(_.read())

        self.__validate_html(self.extension.project, page, doc_root)

        self.writing_page_signal(self, page, full_path, doc_root)
        with open(full_path, 'w', encoding='utf-8') as _:
            transformed = str(self.__page_transform(doc_root))
            _.write('<!DOCTYPE html>\n%s' % transformed)

    def cache_page(self, page):
        """
        Banana banana
        """
        full_path = os.path.join(self.__cache_dir,
                                 self.get_output_folder(page),
                                 page.link.ref)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as _:
            _.write(page.detailed_description)

        page.cached_paths.add(full_path)

    # pylint: disable=no-self-use
    def _get_extension(self):
        return "html"

    def get_output_folder(self, page):
        """
        Banana banana
        """
        if self.extension.project.is_toplevel:
            return ''

        return page.project_name

    def _format_link(self, link, attrs, title):
        out = ''
        assert link

        template = self.get_template('link.html')
        out += '%s' % template.render({'link': link,
                                       'attrs': attrs or '',
                                       'link_title': title})
        return out

    # pylint: disable=unused-argument
    def _format_type_tokens(self, symbol, type_tokens):
        out = ''
        link_before = False

        for tok in type_tokens:
            if isinstance(tok, Link):
                ref, attrs = tok.get_link(self.extension.app.link_resolver)
                if ref:
                    out += self._format_link(ref, attrs, tok.title)
                    link_before = True
                else:
                    if link_before:
                        out += ' '
                    out += tok.title
                    link_before = False
            else:
                if link_before:
                    out += ' '
                out += tok
                link_before = False

        return out

    # pylint: disable=unidiomatic-typecheck
    def _format_linked_symbol(self, symbol):
        out = ""

        if isinstance(symbol, QualifiedSymbol):
            out += self._format_type_tokens(symbol, symbol.type_tokens)

        # FIXME : ugly
        elif hasattr(symbol, "link") and not isinstance(symbol, FieldSymbol):
            ref, attrs = symbol.link.get_link(self.extension.app.link_resolver)
            out += self._format_link(
                ref,
                attrs,
                symbol.link.title)

        if isinstance(symbol, ParameterSymbol):
            out += ' ' + symbol.argname

        elif isinstance(symbol, FieldSymbol) and symbol.member_name:
            out += self._format_type_tokens(symbol, symbol.qtype.type_tokens)
            if symbol.is_function_pointer:
                out = ""

        return out

    def _format_callable_prototype(self, return_value, function_name,
                                   parameters, is_pointer):
        template = self.get_template('callable_prototype.html')

        return template.render({'return_value': return_value,
                                'name': function_name,
                                'parameters': parameters,
                                'is_pointer': is_pointer})

    def __format_parameter_detail(self, name, detail, extra=None):
        extra = extra or {}
        template = self.get_template('parameter_detail.html')
        return template.render({'name': name,
                                'detail': detail,
                                'extra': extra})

    def _format_symbol_descriptions(self, symbols_list):
        detailed_descriptions = []

        for element in symbols_list.symbols:
            if element.skip:
                continue
            if element.detailed_description:
                detailed_descriptions.append(element.detailed_description)

        symbol_type = symbols_list.name
        symbol_descriptions = None
        if detailed_descriptions:
            symbol_descriptions = SymbolDescriptions(
                detailed_descriptions, symbol_type)

        return symbol_descriptions

    def _format_struct(self, struct):
        raw_code = None
        if struct.raw_text is not None:
            raw_code = self._format_raw_code(struct.raw_text)

        members_list = self._format_members_list(struct.members, 'Fields',
                                                 struct)

        template = self.get_template("struct.html")
        out = template.render({"symbol": struct,
                               "struct": struct,
                               "raw_code": raw_code,
                               "members_list": members_list})
        return out

    def _format_enum_member_symbol(self, member):
        template = self.get_template("enum_member.html")
        return template.render({
            'link': member.link,
            'detail': member.formatted_doc,
            'value': str(member.enum_value)})

    def _format_enum(self, enum):
        raw_code = None
        if enum.raw_text is not None:
            raw_code = self._format_raw_code(enum.raw_text)
        members_list = self._format_members_list(enum.members, 'Members',
                                                 enum)
        template = self.get_template("enum.html")
        out = template.render({"symbol": enum,
                               "enum": enum,
                               "raw_code": raw_code,
                               "members_list": members_list})
        return out

    def prepare_page_attributes(self, page):
        """
        Banana banana
        """
        self._current_page = page
        page.output_attrs['html']['scripts'] = OrderedSet()
        page.output_attrs['html']['stylesheets'] = OrderedSet()
        page.output_attrs['html']['extra_html'] = []
        page.output_attrs['html']['edit_button'] = ''
        page.output_attrs['html']['extra_footer_html'] = []
        if Formatter.add_anchors:
            page.output_attrs['html']['scripts'].add(
                os.path.join(HERE, 'assets', 'css.escape.js'))

    def __get_symbols_details(self, page, parent_name=None):
        symbols_details = []
        for symbols_type in self._ordering:
            if not self._order_by_parent:
                symbols_list = page.typed_symbols.get(symbols_type)
            else:
                symbols_list = page.by_parent_symbols[parent_name].get(
                    symbols_type)

            if not symbols_list:
                continue

            symbols_descriptions = self._format_symbol_descriptions(
                symbols_list)

            if symbols_descriptions:
                symbols_details.append(symbols_descriptions)
                if parent_name:
                    if len(symbols_list.symbols) == 1:
                        sym = symbols_list.symbols[0]
                        if sym.unique_name == parent_name:
                            symbols_descriptions.name = None

        return symbols_details

    # pylint: disable=too-many-locals
    def _format_page(self, page):
        symbols_details = []
        by_sections = []
        by_section_symbols = namedtuple('BySectionSymbols',
                                        ['has_parent', 'symbols_details'])

        if not self._order_by_parent:
            symbols_details = self.__get_symbols_details(page)
        else:
            for parent_name in page.by_parent_symbols.keys():
                symbols_details = self.__get_symbols_details(page, parent_name)

                if symbols_details:
                    by_sections.append(by_section_symbols(bool(parent_name),
                                                          symbols_details))

        template = self.get_template('page.html')

        scripts = []
        stylesheets = []

        rel_path = os.path.relpath('.', os.path.join(
            self.get_output_folder(page),
            os.path.dirname(page.link.ref)))

        if Formatter.extra_theme_path:
            js_dir = os.path.join(Formatter.extra_theme_path, 'js')
            try:
                for _ in os.listdir(js_dir):
                    scripts.append(os.path.join(js_dir, _))
            except OSError:
                pass

            css_dir = os.path.join(Formatter.extra_theme_path, 'css')
            try:
                for _ in os.listdir(css_dir):
                    stylesheets.append(os.path.join(css_dir, _))
            except OSError:
                pass

        scripts.extend(page.output_attrs['html']['scripts'])
        stylesheets.extend(page.output_attrs['html']['stylesheets'])
        scripts_basenames = [os.path.basename(script)
                             for script in scripts]
        stylesheets_basenames = [os.path.basename(stylesheet)
                                 for stylesheet in stylesheets]

        Formatter.all_stylesheets.update(stylesheets)
        Formatter.all_scripts.update(scripts)

        out = template.render(
            {'page': page,
             'scripts': scripts_basenames,
             'stylesheets': stylesheets_basenames,
             'rel_path': rel_path,
             'attrs': page.output_attrs['html'],
             'meta': {},
             'symbols_details': symbols_details,
             'sections_details': by_sections,
             'in_toplevel': self.extension.project.is_toplevel}
        )

        return (out, True)

    def _format_prototype(self, function, is_pointer, title):
        if function.return_value:
            return_value = self._format_linked_symbol(function.return_value[0])
        else:
            return_value = None

        parameters = []
        for param in function.parameters:
            parameters.append(self._format_linked_symbol(param))

        return self._format_callable_prototype(return_value,
                                               title, parameters, is_pointer)

    def _format_raw_code(self, code):
        code = html.escape(code)
        template = self.get_template('raw_code.html')
        return template.render({'code': code})

    def _format_parameter_symbol(self, parameter):
        return self.__format_parameter_detail(
            parameter.argname,
            parameter.formatted_doc,
            extra=parameter.extension_contents)

    def _format_field_symbol(self, field):
        template = self.get_template('field_detail.html')
        field.formatted_link = self._format_linked_symbol(field)
        return template.render({'symbol': field,
                                'detail': field.formatted_doc})

    def _format_return_item_symbol(self, return_item):
        template = self.get_template('return_item.html')
        return_item.formatted_link = self._format_linked_symbol(return_item)
        return template.render({'return_item': return_item})

    def _format_return_value_symbol(self, return_value, parent):
        template = self.get_template('multi_return_value.html')
        if return_value[0] is None:
            return_value = return_value[1:]
        return template.render({'return_items': return_value})

    def _format_callable(self, callable_, callable_type, title,
                         is_pointer=False):
        template = self.get_template('callable.html')

        parameters = [p.detailed_description for p in callable_.parameters if
                      p.detailed_description is not None]

        prototype = self._format_prototype(callable_, is_pointer, title)

        return_value_detail = self._format_return_value_symbol(
            callable_.return_value, callable_)

        tags = {}
        if callable_.comment:
            tags = dict(callable_.comment.tags)

        tags.pop('returns', None)
        tags.pop('topic', None)

        out = template.render({'prototype': prototype,
                               'symbol': callable_,
                               'return_value': return_value_detail,
                               'parameters': parameters,
                               'tags': tags,
                               'extra': callable_.extension_contents})

        return out

    def _format_signal_symbol(self, signal):
        title = "%s_callback" % re.sub('-', '_', signal.link.title)
        return self._format_callable(signal, "signal", title)

    def _format_vfunction_symbol(self, vmethod):
        return self._format_callable(vmethod, "virtual method",
                                     '%s' % vmethod.link.title)

    def _format_property_prototype(self, prop, title, type_link):
        template = self.get_template('property_prototype.html')
        prototype = template.render({'property_name': title,
                                     'property_type': type_link})
        return prototype

    def _format_property_symbol(self, prop):
        type_link = self._format_linked_symbol(prop.prop_type)
        prototype = self._format_property_prototype(prop, prop.link.title,
                                                    type_link)
        template = self.get_template('property.html')
        res = template.render({'symbol': prop,
                               'prototype': prototype,
                               'property': prop,
                               'extra': prop.extension_contents})
        return res

    def _format_hierarchy(self, klass):
        hierarchy = []
        children = []
        for _ in klass.hierarchy:
            hierarchy.append(self._format_linked_symbol(_))
        for _ in klass.children.values():
            children.append(self._format_linked_symbol(_))

        if hierarchy or children:
            template = self.get_template("hierarchy.html")
            hierarchy = template.render({'hierarchy': hierarchy,
                                         'children': children,
                                         'klass': klass})
        return hierarchy

    def _format_class_symbol(self, klass):
        hierarchy = self._format_hierarchy(klass)
        template = self.get_template('class.html')
        raw_code = None
        if klass.raw_text is not None:
            raw_code = self._format_raw_code(klass.raw_text)

        members_list = self._format_members_list(klass.members, 'Members',
                                                 klass)

        klass.extension_attributes['is_section_head'] = self._order_by_parent
        return template.render({'symbol': klass,
                                'klass': klass,
                                'hierarchy': hierarchy,
                                'raw_code': raw_code,
                                'members_list': members_list})

    def _format_interface_symbol(self, interface):
        hierarchy = self._format_hierarchy(interface)
        template = self.get_template('interface.html')
        interface.extension_attributes['is_section_head'] = self._order_by_parent
        return template.render({'symbol': interface,
                                'hierarchy': hierarchy})

    def _format_members_list(self, members, member_designation,
                             parent):
        template = self.get_template('member_list.html')
        return template.render({'members': members,
                                'member_designation': member_designation,
                                'parent_is_class': isinstance(parent,
                                                              ClassSymbol)})

    def _format_function(self, function):
        return self._format_callable(function, "method", function.link.title)

    def _format_callback(self, callback):
        return self._format_callable(callback, "callback",
                                     callback.link.title, is_pointer=True)

    def _format_function_macro(self, function_macro):
        template = self.get_template('callable.html')
        prototype = self._format_raw_code(function_macro.original_text)

        parameters = []
        for _ in function_macro.parameters:
            if not _.detailed_description:
                continue
            parameters.append(_.detailed_description)

        return_value_detail = self._format_return_value_symbol(
            function_macro.return_value, function_macro)

        out = template.render({'prototype': prototype,
                               'symbol': function_macro,
                               'return_value': return_value_detail,
                               'parameters': parameters,
                               'callable_type': "function macro",
                               'flags': None,
                               'tags': {},
                               'extra': function_macro.extension_contents})

        return out

    def _format_alias(self, alias):
        template = self.get_template('alias.html')
        aliased_type = self._format_linked_symbol(alias.aliased_type)
        return template.render({'symbol': alias,
                                'alias': alias,
                                'aliased_type': aliased_type})

    def _format_constant(self, constant):
        template = self.get_template('constant.html')
        definition = self._format_raw_code(constant.original_text)
        out = template.render({'symbol': constant,
                               'definition': definition,
                               'constant': constant})
        return out

    def _format_symbol(self, symbol):
        order_by_section = self._order_by_parent and bool(symbol.parent_name)
        symbol.extension_attributes['order_by_section'] = order_by_section
        for csym in symbol.get_children_symbols():
            if csym:
                csym.parent_name = symbol.parent_name
                csym.extension_attributes['order_by_section'] = \
                    order_by_section
                csym.detailed_description = self._format_symbol(csym)

        symbol.formatted_doc = self.format_comment(
            symbol.comment, self.extension.app.link_resolver)

        format_function = self._symbol_formatters.get(type(symbol))
        if format_function:
            return format_function(symbol)

        return None

    def _format_comment(self, comment, link_resolver):
        return self._docstring_formatter.translate_comment(
            comment, link_resolver)

    def __get_theme_files(self, path):
        res = []
        theme_files = os.listdir(path)
        for file_ in theme_files:
            if file_ == 'templates':
                pass
            src = os.path.join(path, file_)
            dest = os.path.basename(src)
            res.append((src, dest))
        return res

    def _get_extra_files(self):
        res = []

        if Formatter.theme_path:
            res.extend(self.__get_theme_files(Formatter.theme_path))
        if Formatter.extra_theme_path:
            res.extend(self.__get_theme_files(Formatter.extra_theme_path))

        for script_path in Formatter.all_scripts:
            dest = os.path.join('js', os.path.basename(script_path))
            res.append((script_path, dest))

        for stylesheet_path in Formatter.all_stylesheets:
            dest = os.path.join('css', os.path.basename(stylesheet_path))
            res.append((stylesheet_path, dest))

        return res

    @staticmethod
    def add_arguments(parser):
        """Banana banana
        """
        group = parser.add_argument_group(
            'Formatter', 'formatter options')

        group.add_argument("--html-theme", action="store",
                           dest="html_theme",
                           help="html theme to use, this can be a url to a"
                           " released tarball on an http server"
                           " (preferably with a ?sha256=param)",
                           default='default')
        group.add_argument("--html-extra-theme", action="store",
                           dest="html_extra_theme",
                           help="Extra stylesheets and scripts")
        group.add_argument("--html-add-anchors", action="store_true",
                           dest="html_add_anchors",
                           help="Add anchors to html headers",
                           default='default')
        group.add_argument("--html-number-headings", action="store_true",
                           dest="html_number_headings",
                           help="Enable html headings numbering")

    def __download_theme(self, uri):
        sha = urllib.parse.parse_qs(uri.query).get('sha256')
        cachedir = appdirs.user_cache_dir("hotdoc", "hotdoc")
        os.makedirs(cachedir, exist_ok=True)

        if sha:
            sha = sha[0]

        if sha and os.path.isdir(os.path.join(cachedir, "themes", sha)):
            return os.path.join(cachedir, "themes", sha)

        print("Downloading %s" % uri.geturl())
        tarball = os.path.join(cachedir, "themes", os.path.basename(uri.path))
        os.makedirs(os.path.dirname(tarball), exist_ok=True)
        try:
            urlretrieve(uri.geturl(), tarball, _download_progress_cb)
        except (TimeoutError, urllib.error.HTTPError) as exce:
            warn('download-theme-error',
                 "Error downloading %s: %s - Using default them" % (
                     tarball, exce))
            return 'default'

        if not sha:
            with open(tarball) as file_:
                sha = hashlib.sha256().update(file_.read()).hexdigest()

        themepath = os.path.join(cachedir, "themes", sha)
        try:
            os.makedirs(os.path.join(themepath))
            with tarfile.open(tarball) as file_:
                file_.extractall(themepath)
        except tarfile.ReadError:
            warn('download-theme-error',
                 "%s is not a supported tarball - Using default theme" %
                 themepath)
            os.rmdir(themepath)
            return 'default'

        return themepath

    def parse_toplevel_config(self, config):
        """Parse @config to setup @self state."""
        if not Formatter.initialized:
            html_theme = config.get('html_theme', 'default')

            if html_theme != 'default':
                uri = urllib.parse.urlparse(html_theme)
                if not uri.scheme:
                    html_theme = config.get_path('html_theme')
                    debug("Using theme located at %s" % html_theme)
                elif uri.scheme.startswith('http'):
                    html_theme = self.__download_theme(uri)

            if html_theme == 'default':
                default_theme = os.path.join(HERE, os.pardir,
                                             'hotdoc_bootstrap_theme', 'dist')

                html_theme = os.path.abspath(default_theme)
                debug("Using default theme")

            theme_meta_path = os.path.join(html_theme, 'theme.json')

            if os.path.exists(theme_meta_path):
                with open(theme_meta_path, 'r') as _:
                    Formatter.theme_meta = json.loads(_.read())

            searchpath = []
            self.__load_theme_templates(searchpath, HERE)

            Formatter.theme_path = html_theme
            if html_theme:
                self.__load_theme_templates(searchpath, html_theme)

            Formatter.extra_theme_path = config.get_path('html_extra_theme')
            if Formatter.extra_theme_path:
                self.__load_theme_templates(searchpath,
                                            Formatter.extra_theme_path)

            Formatter.engine = Engine(
                loader=FileLoader(searchpath, encoding='UTF-8'),
                extensions=[CoreExtension(), CodeExtension()])
            Formatter.engine.global_vars.update({'e': html.escape})

            Formatter.initialized = True

    def get_template(self, name):
        """
        Banana banana
        """
        return Formatter.engine.get_template(name)

    def parse_config(self, config):
        """Banana banana
        """
        self.add_anchors = bool(config.get("html_add_anchors"))
        self.number_headings = bool(config.get("html_number_headings"))
        self._docstring_formatter.parse_config(config)

    def format_navigation(self, project):
        """Banana banana
        """
        try:
            template = self.get_template('site_navigation.html')
        except IOError:
            return None

        return template.render({'project': project})

    def format_subpages(self, page, subpages):
        """Banana banana
        """
        if not subpages:
            return None

        try:
            template = self.get_template('subpages.html')
        except IOError:
            return None

        ret = etree.XML(template.render({'page': page,
                                         'subpages': subpages}))
        assets = ret.xpath('.//*[@src]')
        for asset in assets:
            self.__lookup_asset(asset, self.extension.project, page)

        return ret
