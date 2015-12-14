# -*- coding: utf-8 -*-

import os
import shutil
import pygraphviz as pg

from .symbols import *
from ..utils.simple_signals import Signal
from xml.sax.saxutils import unescape

def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in all_subclasses(s)]

class Formatter(object):
    def __init__ (self, doc_tool):
        self.doc_tool = doc_tool
        self._output = doc_tool.output

        # FIXME: check if we need this level of detail performance-wise
        self.formatting_symbol_signals = {}
        symbol_subclasses = all_subclasses (Symbol)
        symbol_subclasses.append(Symbol)
        for klass in symbol_subclasses:
            self.formatting_symbol_signals[klass] = Signal()
        qs_subclasses = all_subclasses(QualifiedSymbol)
        qs_subclasses.append(QualifiedSymbol)
        for klass in qs_subclasses:
            self.formatting_symbol_signals[klass] = Signal()

    def _create_hierarchy_graph (self, hierarchy):
        # FIXME: handle multiple inheritance
        graph = pg.AGraph(directed=True, strict=True)

        for pair in hierarchy:
            parent_link = pair[0].get_type_link()
            child_link = pair[1].get_type_link()

            graph.add_node(parent_link.title, URL=parent_link.get_link(),
                    style="rounded", shape="box")
            graph.add_node(child_link.title, URL=child_link.get_link(),
                    style="rounded", shape="box")

            graph.add_edge (parent_link.title, child_link.title)

        return graph

    def __update_children_comments(self, symbol):
        # FIXME: for live previewing, editing parameters doesn't work
        # unless this is called, refactor correctly.
        if not symbol.comment:
            return

        for param in symbol.parameters:
            param.comment = symbol.comment.params.get(param.argname)

        if symbol.return_value:
            rv_tag = symbol.comment.tags.get('returns')
            symbol.return_value.comment = comment_from_tag(rv_tag)

    def patch_page(self, page, symbol):
        raise NotImplementedError

    def format_symbol (self, symbol):
        #if isinstance(symbol, FunctionSymbol):
        #    self.__update_children_comments(symbol)

        self.__format_symbols(symbol.get_children_symbols())

        # We only need to resolve qualified symbols now because
        # they're referring to an actual type, not referred to.
        if isinstance (symbol, QualifiedSymbol):
            symbol.resolve_links(self.doc_tool.link_resolver)

        if type (symbol) in self.formatting_symbol_signals:
            res = self.formatting_symbol_signals[type(symbol)](symbol)

            if False in res:
                return False

            res = self.formatting_symbol_signals[Symbol](symbol)

            if False in res:
                return False

        symbol.formatted_doc = self.__format_doc (symbol.comment)
        out, standalone = self._format_symbol (symbol)
        symbol.detailed_description = out

        # FIXME: figure out whether this approach is desirable
        if standalone:
            self._write_page (symbol)

        return True

    def format (self, page):
        self.__format_page (page)
        self.__copy_extra_files ()

    def __format_symbols(self, symbols):
        for symbol in symbols:
            if symbol is None:
                continue
            symbol.skip = not self.format_symbol(symbol)

    def __format_page (self, page):
        if page.is_stale:
            self.doc_tool.update_doc_parser(page.extension_name)
            self.__format_symbols(page.symbols)
            page.detailed_description = self.doc_tool.formatter._format_page (page)[0]
            self.doc_tool.formatter._write_page (page)

        for pagename in page.subpages:
            cpage = self.doc_tool.doc_tree.get_page(pagename)
            formatter = self.doc_tool.get_formatter(cpage.extension_name)

            # This is a bit funky, might be better to not have
            # other code use doc_tool.formatter, but a provided one.
            if formatter and formatter != self.doc_tool.formatter:
                self.doc_tool.formatter = formatter
                self.doc_tool.formatter.format(cpage)
            else:
                self.__format_page (cpage)
            self.doc_tool.formatter = self


    def __copy_extra_files (self):
        asset_path = os.path.join (self.doc_tool.output, 'assets')
        if not os.path.exists (asset_path):
            os.mkdir (asset_path)

        for f in self._get_extra_files():
            basename = os.path.basename (f)
            path = os.path.join (asset_path, basename)
            if os.path.isfile(f):
                shutil.copy (f, path)
            elif os.path.isdir(f):
                shutil.rmtree(path, ignore_errors=True)
                shutil.copytree(f, path)

    def _write_page (self, page):
        path = os.path.join (self._output, page.link.ref)
        with open (path, 'w') as f:
            out = page.detailed_description
            f.write (out.encode('utf-8'))

    def _format_doc_string (self, docstring):
        if not docstring:
            return ""

        out = ""
        docstring = unescape (docstring)
        rendered_text = self.doc_tool.doc_parser.translate (docstring, 'html')
        return rendered_text

    def __format_doc (self, comment):
        out = ""
        if comment and comment.description:
            out = self.doc_tool.doc_parser.translate_comment (comment, 'html')
        return out

    def _get_extra_files (self):
        return []
