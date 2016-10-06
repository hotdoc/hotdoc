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

"""
This module defines a base Formatter class
"""

import os
import shutil

from schema import Schema, Optional
from hotdoc.core.doc_tree import Page

import pygraphviz as pg
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.simple_signals import Signal
from hotdoc.utils.utils import recursive_overwrite, OrderedSet


Page.meta_schema[Optional('extra')] = Schema({unicode: object})


def _create_hierarchy_graph(hierarchy):
    # FIXME: handle multiple inheritance
    graph = pg.AGraph(directed=True, strict=True)

    for pair in hierarchy:
        parent_link = pair[0].get_type_link()
        child_link = pair[1].get_type_link()

        graph.add_node(parent_link.title, URL=parent_link.get_link(),
                       style="rounded", shape="box")
        graph.add_node(child_link.title, URL=child_link.get_link(),
                       style="rounded", shape="box")

        graph.add_edge(parent_link.title, child_link.title)

    return graph


class Formatter(Configurable):
    """Formats and writes `doc_tree.Page` and `symbols.Symbol`

    Subclasses should implement the protected methods.
    """
    formatting_page_signal = Signal()
    formatting_symbol_signal = Signal()
    writing_page_signal = Signal()
    get_extra_files_signal = Signal()
    extra_assets = None

    def __init__(self):
        self._current_page = None

    # pylint: disable=no-self-use
    def _get_assets_path(self):
        """
        Banana banana
        """
        return 'assets'

    def format_symbol(self, symbol, link_resolver):
        """
        Format a symbols.Symbol
        """
        if not symbol:
            return ''

        for csym in symbol.get_children_symbols():
            self.format_symbol(csym, link_resolver)

        res = Formatter.formatting_symbol_signal(self, symbol)

        if False in res:
            return False

        symbol.formatted_doc = self.format_comment(symbol.comment,
                                                   link_resolver)
        # pylint: disable=unused-variable
        out, standalone = self._format_symbol(symbol)
        symbol.detailed_description = out

        return symbol.detailed_description

    def __copy_extra_assets(self, output):
        for src in self.extra_assets or []:
            dest = os.path.join(output, os.path.basename(src))

            destdir = os.path.dirname(dest)
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            if os.path.isdir(src):
                recursive_overwrite(src, dest)
            elif os.path.isfile(src):
                shutil.copyfile(src, dest)

    def __copy_extra_files(self, assets_path):
        if not os.path.exists(assets_path):
            os.mkdir(assets_path)

        extra_files = self._get_extra_files()

        for ex_files in self.get_extra_files_signal(self):
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

    def write_page(self, page, output):
        """
        Banana banana
        """
        path = os.path.join(output, page.link.ref)
        self.writing_page_signal(self, page, path)
        with open(path, 'w') as _:
            out = page.detailed_description
            _.write(out.encode('utf-8'))
        self.__copy_extra_files(os.path.join(output, 'assets'))
        self.__copy_extra_assets(output)

    def patch_page(self, page, symbol):
        """
        Subclasses should implement this in order to allow
        live patching of the documentation.
        """
        raise NotImplementedError

    def format_page(self, page):
        """
        Banana banana
        """
        Formatter.formatting_page_signal(self, page)
        return self._format_page(page)

    def get_output_folder(self):
        """
        Get the output folder for this formatter

        Returns:
            str: The output subfolder.
        """
        return ''

    def _format_page(self, page):
        """
        Banana banana
        """
        raise NotImplementedError

    def _format_symbol(self, symbol):
        """
        Banana banana
        """
        raise NotImplementedError

    def _format_comment(self, comment, link_resolver):
        raise NotImplementedError

    def format_comment(self, comment, link_resolver):
        """Format a comment

        Args:
            comment: hotdoc.core.comment_block.Comment, the code comment
            to format. Can be None, in which case the empty string will
            be returned.
        Returns:
            str: The formatted comment.
        """
        if comment:
            return self._format_comment(comment, link_resolver)

        return ''

    # pylint: disable=no-self-use
    def _get_extra_files(self):
        return []

    # pylint: disable=no-self-use
    def prepare_page_attributes(self, page):
        """
        Banana banana
        """
        self._current_page = page

    @staticmethod
    def add_arguments(parser):
        """Banana banana
        """
        group = parser.add_argument_group(
            'Base formatter', 'base formatter options')
        group.add_argument(
            "--extra-assets",
            help="Extra asset folders to copy in the output",
            action='append', dest='extra_assets', default=[])

    @staticmethod
    def parse_config(doc_repo, config):
        """Banana banana
        """
        Formatter.extra_assets = OrderedSet(config.get_paths('extra_assets'))
