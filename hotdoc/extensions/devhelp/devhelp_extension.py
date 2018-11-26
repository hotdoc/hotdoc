# -*- coding: utf-8 -*-
#
# Copyright © 2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2016 Collabora Ltd
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

# pylint: disable=missing-docstring

import os

from collections import defaultdict, namedtuple
from lxml import etree

from hotdoc.core.symbols import (
    FunctionSymbol, ClassSymbol, StructSymbol, EnumSymbol, PropertySymbol,
    SignalSymbol, ConstantSymbol, FunctionMacroSymbol, CallbackSymbol,
    InterfaceSymbol, AliasSymbol, VFunctionSymbol, ExportedVariableSymbol,
    FieldSymbol, MethodSymbol, EnumMemberSymbol, ConstructorSymbol)
from hotdoc.core.extension import Extension
from hotdoc.utils.utils import recursive_overwrite

DESCRIPTION =\
    """
An extension to generate devhelp indexes.
"""

BOILERPLATE =\
    u"""<?xml version="1.0"?>
<book xmlns="http://www.devhelp.net/book" title="%s" link="%s" \
author="hotdoc" name="%s" version="2" language="%s"/>
"""

HERE = os.path.dirname(__file__)


FormattedSymbol = namedtuple('FormattedSymbol',
                             ['type_', 'ref', 'display_name'])


TYPE_MAP = {
    FunctionSymbol: 'function',
    ClassSymbol: 'class',
    StructSymbol: 'struct',
    EnumSymbol: 'enum',
    EnumMemberSymbol: 'member',
    PropertySymbol: 'property',
    SignalSymbol: 'signal',
    ConstantSymbol: 'macro',
    FunctionMacroSymbol: 'macro',
    CallbackSymbol: 'function',
    InterfaceSymbol: 'interface',
    AliasSymbol: 'alias',
    VFunctionSymbol: 'vfunc',
    ExportedVariableSymbol: 'extern',
    FieldSymbol: 'field',
    MethodSymbol: 'function',
    ConstructorSymbol: 'function',
}


class DevhelpExtension(Extension):
    extension_name = 'devhelp-extension'
    argument_prefix = 'devhelp'

    activated = False
    __connected = False
    __resolved_symbols_map = {}

    def __init__(self, app, project):
        Extension.__init__(self, app, project)
        self.__ext_languages = defaultdict(set)

    def __writing_page_cb(self, formatter, page, path, lxml_tree):
        html_path = os.path.join(self.app.output, 'html')
        relpath = os.path.relpath(path, html_path)

        DevhelpExtension.__resolved_symbols_map[relpath] = [
            FormattedSymbol(TYPE_MAP.get(type(sym)),
                            sym.link.ref, sym.link.title)
            for sym in page.symbols]

    def __format_subs(self, tree, pnode, page, subproject=None):
        for name in page.subpages:
            cpage = tree.get_pages()[name]

            subtree = None
            ext = os.path.splitext(cpage.name)[1]
            if ext.endswith('.json'):
                subproject = tree.project.subprojects[cpage.name]
                subtree = subproject.tree
                cpage = subtree.root

            ref = cpage.link.ref
            if subproject:
                ref = os.path.join(subproject.sanitized_name, ref)
            node = etree.Element('sub',
                                 attrib={'name': cpage.title,
                                         'link': ref})

            pnode.append(node)
            if subtree:
                self.__format_subs(subtree, node, cpage, subproject)
            else:
                self.__format_subs(tree, node, cpage)

    def __format(self, project):
        oname = project.sanitized_name
        title = '%s %s' % (project.project_name, project.project_version)

        opath = os.path.join(self.app.output, 'devhelp')

        boilerplate = BOILERPLATE % (
            title,
            project.tree.root.link.ref,
            oname,
            'C')

        root = etree.fromstring(boilerplate)

        chapter_node = etree.Element('chapters')
        self.__format_subs(project.tree, chapter_node,
                           project.tree.root)
        root.append(chapter_node)

        funcs_node = etree.Element('functions')
        for _, symbols in DevhelpExtension.__resolved_symbols_map.items():
            for sym in symbols:
                if sym.type_ is None:
                    continue
                node = etree.Element('keyword',
                                     attrib={'type': sym.type_,
                                             'name': sym.display_name,
                                             'link': sym.ref})
                funcs_node.append(node)

        root.append(funcs_node)

        index_path = os.path.join(opath, oname + '.devhelp2')

        if not os.path.exists(opath):
            os.makedirs(opath)

        tree = etree.ElementTree(root)
        tree.write(index_path, pretty_print=True,
                   encoding='utf-8', xml_declaration=True)

        return opath

    def __project_written_out_cb(self, project):
        self.__format(project)

    # pylint: disable=no-self-use
    def __formatted_cb(self, app):
        html_path = os.path.join(app.output, 'html')
        dh_html_path = os.path.join(app.output, 'devhelp')
        recursive_overwrite(html_path, dh_html_path)

        # Remove some stuff not relevant in devhelp
        with open(os.path.join(dh_html_path, 'assets', 'css',
                               'devhelp.css'), 'w') as _:
            _.write('[data-hotdoc-role="navigation"] {display: none;}\n')

    @staticmethod
    def __formatting_page_cb(formatter, page):
        page.output_attrs['html']['stylesheets'].add(
            os.path.join(HERE, 'devhelp.css'))

    def setup(self):
        super(DevhelpExtension, self).setup()
        if not DevhelpExtension.activated:
            return

        for ext in self.project.extensions.values():
            ext.formatter.writing_page_signal.connect(self.__writing_page_cb)
            ext.formatter.formatting_page_signal.connect(
                self.__formatting_page_cb)

        if DevhelpExtension.__connected:
            return

        self.project.written_out_signal.connect_after(
            self.__project_written_out_cb)
        self.app.formatted_signal.connect_after(self.__formatted_cb)
        DevhelpExtension.__connected = True

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('Devhelp extension',
                                          DESCRIPTION)
        group.add_argument('--devhelp-activate',
                           action="store_true",
                           help="Activate the devhelp extension",
                           dest='devhelp_activate')

    def parse_toplevel_config(self, config):
        super(DevhelpExtension, self).parse_toplevel_config(config)
        DevhelpExtension.activated = bool(
            config.get('devhelp_activate', False))


def get_extension_classes():
    return [DevhelpExtension]
