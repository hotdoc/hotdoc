# -*- coding: utf-8 -*-

import os
import shutil
import CommonMark
import pygraphviz as pg

from xml.sax.saxutils import unescape

from .symbols import (Symbol, ReturnValueSymbol, ParameterSymbol, FieldSymbol,
        ClassSymbol, QualifiedSymbol, CallbackSymbol)
from .sections import Page
from ..utils.simple_signals import Signal
from ..utils.loggable import progress_bar

def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in all_subclasses(s)]

class Formatter(object):
    def __init__ (self, doc_tool):
        self.doc_tool = doc_tool
        self._output = doc_tool.output

        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}

        self.formatting_symbol_signals = {}
        symbol_subclasses = all_subclasses (Symbol)
        symbol_subclasses.append(Symbol)
        for klass in symbol_subclasses:
            self.formatting_symbol_signals[klass] = Signal()

        self.fill_index_columns_signal = Signal()
        self.fill_index_row_signal = Signal()

        # Hardcoded for now
        self.__cmp = CommonMark.DocParser()
        self.__cmr = CommonMark.HTMLRenderer()

    def _create_hierarchy_graph (self, hierarchy):
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

    def __update_progress (self):
        if self.__progress_bar is None:
            return

        if self.__total_pages == 0:
            return

        percent = float (self.__total_rendered_pages) / float (self.__total_pages)
        self.__progress_bar.update (percent, "%d / %d" %
                (self.__total_rendered_pages, self.__total_pages))

    def format_symbol (self, symbol):
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
        if standalone:
            self._write_page (symbol)

        if out and type(symbol) not in [ReturnValueSymbol,
                ParameterSymbol, FieldSymbol] and False:
            row = [symbol.link, symbol.get_type_name()]
            if symbol.comment:
                row.append (os.path.basename(symbol.comment.filename))
            else:
                row.append ('')
            self.fill_index_row_signal (symbol, row)
            self.__index_rows.append (row)

        return True

    def __get_subpages_count (self, page):
        count = 1
        for subpage in page.subpages:
            count += self.__get_subpages_count (subpage)
        return count

    def format (self, page):
        self.__format_page (page)
        self.__copy_extra_files ()

    def __format_symbols(self, symbols):
        for symbol in symbols:
            if symbol is None:
                continue
            self.__format_symbols (symbol.get_children_symbols())
            symbol.skip = not self.format_symbol(symbol)

    def __format_page (self, page):
        out = ""
        self.__format_symbols(page.symbols)
        page.detailed_description = self.doc_tool.formatter._format_page (page)[0]
        self.doc_tool.formatter._write_page (page)
        for cpage in page.subpages:
            if cpage.formatter:
                self.doc_tool.formatter = cpage.formatter
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
            shutil.copy (f, path)

    def __write_API_index (self, content):
        path = os.path.join (self._output, 'api_index.html')
        with open (path, 'w') as f:
            f.write (content.encode('utf-8'))

    def __write_hierarchy (self, content):
        path = os.path.join (self._output, 'object_hierarchy.html')
        with open (path, 'w') as f:
            f.write (content.encode('utf-8'))

    def _write_page (self, page):
        path = os.path.join (self._output, page.link.ref)
        #print "Writing", path
        with open (path, 'w') as f:
            out = page.detailed_description
            f.write (out.encode('utf-8'))

    def _format_doc_string (self, docstring):
        if not docstring:
            return ""

        out = ""
        docstring = unescape (docstring)
        docstring = self.doc_tool.doc_parser.translate (docstring)
        ast = self.__cmp.parse (docstring.encode('utf-8'))
        rendered_text = self.__cmr.render(ast)
        return rendered_text

    def __format_doc (self, comment):
        out = ""
        if comment:
            out += self._format_doc_string (comment.description)
        return out

    def __warn_not_implemented (self, func):
        if func in self.__not_implemented_methods:
            return
        self.__not_implemented_methods [func] = True

    # Virtual methods

    def _get_extension (self):
        """
        The extension to append to the filename
        ('markdown', 'html')
        """
        self.__warn_not_implemented (self._get_extension)
        return ""

    def _get_extra_files (self):
        return []
