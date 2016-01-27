# -*- coding: utf-8 -*-

"""
This module defines a base Formatter class
"""

import os
import shutil
from xml.sax.saxutils import unescape

import pygraphviz as pg
from hotdoc.core.symbols import QualifiedSymbol
from hotdoc.utils.simple_signals import Signal
from hotdoc.utils.utils import recursive_overwrite


def _create_hierarchy_graph(hierarchy):
    """
    Utility function
    """
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
    """
    The base Formatter class
    """
    formatting_page_signal = Signal()

    def __init__(self, doc_tool):
        self.doc_tool = doc_tool
        self._output = doc_tool.output

        self.formatting_symbol_signal = Signal()
        self.current_page = None

        self._docstring_formatter = None
        self._standalone_doc_formatter = None

    # pylint: disable=no-self-use
    def get_assets_path(self):
        """
        Banana banana
        """
        return ''

    def format_symbol(self, symbol):
        """
        Format a symbols.Symbol
        """
        if not symbol:
            return ''

        for csym in symbol.get_children_symbols():
            self.format_symbol(csym)

        # We only need to resolve qualified symbols now because
        # they're referring to an actual type, not referred to.
        if isinstance(symbol, QualifiedSymbol):
            symbol.resolve_links(self.doc_tool.link_resolver)

        res = self.formatting_symbol_signal(self, symbol)

        if False in res:
            return False

        symbol.formatted_doc = self.format_comment(symbol.comment)
        out, standalone = self._format_symbol(symbol)
        symbol.detailed_description = out

        # FIXME: figure out whether this approach is desirable
        if standalone:
            self.write_page(symbol)

        return symbol.detailed_description

    def copy_extra_files(self):
        """
        Banana banana
        """
        asset_path = self.doc_tool.get_assets_path()
        if not os.path.exists(asset_path):
            os.mkdir(asset_path)

        for src, dest in self._get_extra_files():
            dest = os.path.join(asset_path, dest)

            destdir = os.path.dirname(dest)
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            if os.path.isfile(src):
                shutil.copy(src, dest)
            elif os.path.isdir(src):
                recursive_overwrite(src, dest)

    def write_page(self, page):
        """
        Banana banana
        """
        path = os.path.join(self._output, page.link.ref)
        with open(path, 'w') as _:
            out = page.detailed_description
            _.write(out.encode('utf-8'))

    def format_docstring(self, docstring):
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
        rendered_text = self._docstring_formatter.translate(docstring)
        return rendered_text

    def docstring_to_native(self, docstring):
        """formats a doc string with the currently set doctool.doc_parser.
        """
        if not docstring:
            return ""

        if not self._standalone_doc_formatter:
            return ""

        docstring = unescape(docstring)
        rendered_text = self._standalone_doc_formatter.translate(docstring)
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

    def format_comment(self, comment):
        """Convenience function wrapping `format_docstring`.

        Args:
            comment: hotdoc.core.comment_block.Comment, the code comment
            to format.
                Can be None, in which case the empty string will be returned.
        Returns:
            str: The comment formatted to the chosen format.
        """
        if comment:
            return self.format_docstring(comment.description)

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
