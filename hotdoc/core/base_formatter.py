# -*- coding: utf-8 -*-

"""
This module defines a base Formatter class
"""

import os
import shutil
from xml.sax.saxutils import unescape

import pygraphviz as pg
from hotdoc.utils.simple_signals import Signal
from hotdoc.utils.utils import recursive_overwrite


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


class Formatter(object):
    """Formats and writes `doc_tree.Page` s and `symbols.Symbol` s

    Subclasses should implement the protected methods.
    """
    formatting_page_signal = Signal()
    formatting_symbol_signal = Signal()
    editing_server = None

    def __init__(self):
        self.current_page = None

        self._docstring_formatter = None
        self._standalone_doc_formatter = None

    # pylint: disable=no-self-use
    def get_assets_path(self):
        """
        Banana banana
        """
        return ''

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

    def copy_extra_files(self, assets_path):
        """
        Banana banana
        """
        if not os.path.exists(assets_path):
            os.mkdir(assets_path)

        for src, dest in self._get_extra_files():
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
        with open(path, 'w') as _:
            out = page.detailed_description
            _.write(out.encode('utf-8'))

    def format_docstring(self, docstring, link_resolver):
        """Formats a doc string.

        You don't need to unescape the docstring.

        Args:
            docstring: str, the code documentation string to format.
                Can be none, in which case the empty string will be returned.

        Returns:
            str: the formatted docstring.
        """
        if not docstring:
            return ""

        if not self._docstring_formatter:
            return ""

        docstring = unescape(docstring)
        rendered_text = self._docstring_formatter.translate(docstring,
                                                            link_resolver)
        return rendered_text

    def docstring_to_native(self, docstring, link_resolver):
        """formats a doc string with the currently set doctool.doc_parser.
        """
        if not docstring:
            return ""

        if not self._standalone_doc_formatter:
            return ""

        docstring = unescape(docstring)
        rendered_text = self._standalone_doc_formatter.translate(
            docstring, link_resolver)
        return rendered_text

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
        raise NotImplementedError

    def _format_symbol(self, symbol):
        """
        Banana banana
        """
        raise NotImplementedError

    def format_comment(self, comment, link_resolver):
        """Convenience function wrapping `format_docstring`.

        Args:
            comment: hotdoc.core.comment_block.Comment, the code comment
            to format.
                Can be None, in which case the empty string will be returned.
        Returns:
            str: The comment formatted to the chosen format.
        """
        if comment:
            return self.format_docstring(comment.description,
                                         link_resolver)

        return ''

    # pylint: disable=no-self-use
    def _get_extra_files(self):
        return []

    # pylint: disable=no-self-use
    def prepare_page_attributes(self, page):
        """
        Banana banana
        """
        pass

    @classmethod
    def add_arguments(cls, parser):
        """Banana banana
        """
        if cls != Formatter:
            return

        group = parser.add_argument_group(
            'Base formatter', 'base formatter options')
        group.add_argument("--editing-server", action="store",
                           dest="editing_server", help="Editing server url,"
                           " if provided, an edit button will be added")

    @classmethod
    def parse_config(cls, wizard):
        """Banana banana
        """
        if cls != Formatter:
            return

        Formatter.editing_server = wizard.config.get('editing_server')
