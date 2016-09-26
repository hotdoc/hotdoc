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

import os
import re
import shutil

from collections import defaultdict
from collections import OrderedDict
from lxml import etree

from hotdoc.core.base_extension import BaseExtension
from hotdoc.core.base_formatter import Formatter
from hotdoc.core.symbols import *
from hotdoc.utils.loggable import error
from hotdoc.utils.utils import recursive_overwrite

DESCRIPTION =\
"""
An extension to generate devhelp indexes.
"""

BOILERPLATE=\
u"""<?xml version="1.0"?>
<!DOCTYPE book PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "">
<book xmlns="http://www.devhelp.net/book" title="%s" link="%s" \
author="hotdoc" name="%s" version="2" language="%s"/>
"""

HERE = os.path.dirname(__file__)

class FormattedSymbol(object):
    def __init__(self, sym, subfolder):
        self.type_ = TYPE_MAP.get(type(sym))
        self.ref = os.path.join(subfolder, sym.link.ref)
        self.display_name = sym.link.title

TYPE_MAP = {
    FunctionSymbol: 'function',
    ClassSymbol: 'class',
    StructSymbol: 'struct',
    EnumSymbol: 'enum',
    PropertySymbol: 'property',
    SignalSymbol: 'signal',
    ConstantSymbol: 'macro',
    FunctionMacroSymbol: 'macro',
    CallbackSymbol: 'function',
    InterfaceSymbol: 'interface',
    AliasSymbol: 'alias',
    VFunctionSymbol: 'vfunc',
    ExportedVariableSymbol: 'extern',
}


class DevhelpExtension(BaseExtension):
    extension_name='devhelp-extension'
    argument_prefix='devhelp'
    activated = False

    def __init__(self, doc_repo):
        BaseExtension.__init__(self, doc_repo)
        self.__ext_languages = defaultdict(set)
        self.__resolved_symbols_map = {}

    def __writing_page_cb(self, formatter, page, path):
        html_path = os.path.join(self.doc_repo.output, 'html')
        relpath = os.path.relpath(path, html_path)

        dirname = os.path.dirname(relpath)
        self.__resolved_symbols_map[relpath] = [FormattedSymbol(sym, dirname) for sym in page.symbols]

    def __format_subs(self, doc_tree, pnode, page):
        for name in page.subpages:
            cpage = doc_tree.get_pages()[name]
            if cpage.extension_name == 'gi-extension':
                ref = 'c/%s' % cpage.link.ref
            else:
                ref = cpage.link.ref

            node = etree.Element('sub',
                attrib = {'name': cpage.title,
                          'link': ref})
            pnode.append(node)
            self.__format_subs(doc_tree, node, cpage)

    def __format(self, doc_repo):
        oname = doc_repo.project_name
        oname = re.sub('\W+', '-', oname)
        title = doc_repo.project_name
        if doc_repo.project_version:
            oname += '-%s' % doc_repo.project_version
            title += ' %s' % doc_repo.project_version

        opath = os.path.join(self.doc_repo.output, 'devhelp', oname)

        boilerplate = BOILERPLATE % (
            title,
            doc_repo.doc_tree.root.link.ref,
            oname,
            'C')

        root = etree.fromstring(boilerplate)

        chapter_node = etree.Element('chapters')
        self.__format_subs(doc_repo.doc_tree, chapter_node, doc_repo.doc_tree.root)
        root.append(chapter_node)

        funcs_node = etree.Element('functions')
        for page, symbols in self.__resolved_symbols_map.iteritems():
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

    def __formatted_cb(self, doc_repo):
        dh_html_path = self.__format(doc_repo)
        formatter = self.doc_repo.extensions['core'].get_formatter('html')
        html_path = os.path.join(self.doc_repo.output,
                formatter.get_output_folder())

        recursive_overwrite(html_path, dh_html_path)

        # Remove some stuff not relevant in devhelp
        with open(os.path.join(dh_html_path, 'assets', 'css',
            'devhelp.css'), 'w') as _:
            _.write('[data-hotdoc-role="navigation"] {display: none;}\n')

    def __formatting_page_cb(self, formatter, page):
        page.output_attrs['html']['stylesheets'].add(
            os.path.join(HERE, 'devhelp.css'))

    def setup(self):
        if not DevhelpExtension.activated:
            return

        # FIXME update the index someday.
        if self.doc_repo.incremental:
            return

        Formatter.writing_page_signal.connect(self.__writing_page_cb)
        Formatter.formatting_page_signal.connect(self.__formatting_page_cb)
        self.doc_repo.formatted_signal.connect_after(self.__formatted_cb)

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('Devhelp extension',
                DESCRIPTION)
        group.add_argument('--devhelp-activate', action="store_true",
                help="Activate the devhelp extension", dest='devhelp_activate')

    @staticmethod
    def parse_config(doc_repo, config):
        DevhelpExtension.activated = bool(config.get('devhelp_activate', False))
        if DevhelpExtension.activated and config.get('project_name', None) is None:
            error('invalid-config',
                'To activate the devhelp extension, --project-name has to be '
                'specified.')


def get_extension_classes():
    return [DevhelpExtension]
