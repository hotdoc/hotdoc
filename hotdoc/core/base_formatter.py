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

    # pylint: disable=no-self-use
    def get_assets_path(self):
        """
        Banana banana
        """
        return ''

    def format_symbol(self, symbol):
        """
        Banana banana
        """
        self._format_symbols(symbol.get_children_symbols())

        # We only need to resolve qualified symbols now because
        # they're referring to an actual type, not referred to.
        if isinstance(symbol, QualifiedSymbol):
            symbol.resolve_links(self.doc_tool.link_resolver)

        res = self.formatting_symbol_signal(symbol)

        if False in res:
            return False

        symbol.formatted_doc = self._format_doc(symbol.comment)
        out, standalone = self._format_symbol(symbol)
        symbol.detailed_description = out

        # FIXME: figure out whether this approach is desirable
        if standalone:
            self.write_page(symbol)

        return True

    def format(self, page):
        """
        Formats a given page and its subpages
        """
        self.__format_page(page)
        self.__copy_extra_files()

    def _format_symbols(self, symbols):
        for symbol in symbols:
            if symbol is None:
                continue
            symbol.skip = not self.format_symbol(symbol)

    def __format_page(self, page):
        self.current_page = page

        if page.is_stale:
            page.reset_output_attributes()
            self._prepare_page_attributes(page)
            Formatter.formatting_page_signal(self, page)
            self.doc_tool.update_doc_parser(page.extension_name)
            self._format_symbols(page.symbols)
            self.doc_tool.doc_tree.page_parser.rename_page_links(page)
            page.detailed_description =\
                self.doc_tool.formatter.format_page(page)[0]
            self.doc_tool.formatter.write_page(page)

        for pagename in page.subpages:
            cpage = self.doc_tool.doc_tree.get_page(pagename)
            formatter = self.doc_tool.get_formatter(cpage.extension_name)

            # This is a bit funky, might be better to not have
            # other code use doc_tool.formatter, but a provided one.
            if formatter and formatter != self.doc_tool.formatter:
                self.doc_tool.formatter = formatter
                self.doc_tool.formatter.format(cpage)
            else:
                self.__format_page(cpage)
            self.doc_tool.formatter = self

    def __copy_extra_files(self):
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

    def _format_doc_string(self, docstring):
        if not docstring:
            return ""

        docstring = unescape(docstring)
        rendered_text = self.doc_tool.doc_parser.translate(docstring, 'html')
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

    def _format_doc(self, comment):
        out = ""
        if comment and comment.description:
            out = self.doc_tool.doc_parser.translate_comment(comment, 'html')
        return out

    # pylint: disable=no-self-use
    def _get_extra_files(self):
        return []

    # pylint: disable=no-self-use
    def _prepare_page_attributes(self, page):
        pass
