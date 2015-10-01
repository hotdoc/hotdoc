# -*- coding: utf-8 -*-

import os
import shutil
import CommonMark
import pygraphviz as pg

from xml.sax.saxutils import unescape

from .doc_tool import ConfigError
from .symbols import (Symbol, ReturnValueSymbol, ParameterSymbol, FieldSymbol,
        ClassSymbol)
from .sections import Page
from ..utils.simple_signals import Signal
from ..utils.loggable import progress_bar

def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in all_subclasses(s)]

class Formatter(object):
    def __init__ (self, doc_tool):
        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}

        self.formatting_symbol_signals = {}
        symbol_subclasses = all_subclasses (Symbol)
        symbol_subclasses.append(Symbol)
        for klass in symbol_subclasses:
            self.formatting_symbol_signals[klass] = Signal()

        self.fill_index_columns_signal = Signal()
        self.fill_index_row_signal = Signal()
        self.doc_tool = doc_tool
        self._output = self.doc_tool.output

        # Hardcoded for now
        self.__cmp = CommonMark.DocParser()
        self.__cmr = CommonMark.HTMLRenderer()
        self.__global_hierarchy = []

    def set_global_hierarchy (self, hierarchy):
        """
        A bit ugly for now, will be changed when C++ support is
        implemented.
        For now the extension provides a list of 2-tuple (parent->child)
        """
        self.__global_hierarchy = hierarchy

    def format (self):
        self.__total_pages = 0
        self.__total_rendered_pages = 0
        for page in self.doc_tool.pages:
            self.__total_pages += self.__get_subpages_count (page)

        self.__progress_bar = progress_bar.get_progress_bar ()
        if self.__progress_bar is not None:
            self.__progress_bar.set_header("Rendering Sections (2 / 2)")
            self.__progress_bar.clear()
            self.__update_progress ()
        
        index_columns = ['Name', 'Type', 'In']
        self.__index_rows = []
        self.fill_index_columns_signal (index_columns)

        for page in self.doc_tool.pages:
            self.__format_page (page)

        if self.doc_tool.page_parser.create_object_hierarchy:
            graph = self.__create_hierarchy_graph ()
            hierarchy = self._format_class_hierarchy (graph)
            if hierarchy:
                self.__write_hierarchy (hierarchy)

        if self.doc_tool.page_parser.create_api_index:
            api_index = self._format_api_index (index_columns, self.__index_rows)
            if api_index:
                self.__write_API_index (api_index)

        self.__copy_extra_files ()

    def __create_hierarchy_graph (self):
        graph = pg.AGraph(directed=True, strict=True)

        for pair in self.__global_hierarchy:
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
            self.__write_symbol (symbol)

        if out and type(symbol) not in [ReturnValueSymbol,
                ParameterSymbol, FieldSymbol]:
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

    def __format_page (self, page):
        out = ""
        page.format_symbols ()
        page.detailed_description = self._format_page (page)[0]
        self.__write_symbol (page)
        self.__total_rendered_pages += 1
        self.__update_progress()

        for page in page.subpages:
            self.__format_page (page)

    def __copy_extra_files (self):
        for f in self._get_extra_files():
            basename = os.path.basename (f)
            shutil.copy (f, os.path.join (self._output, basename))

    def __write_API_index (self, content):
        path = os.path.join (self._output, 'api_index.html')
        with open (path, 'w') as f:
            f.write (content.encode('utf-8'))

    def __write_hierarchy (self, content):
        path = os.path.join (self._output, 'object_hierarchy.html')
        with open (path, 'w') as f:
            f.write (content.encode('utf-8'))

    def __write_symbol (self, symbol):
        path = os.path.join (self._output, symbol.link.ref)
        with open (path, 'w') as f:
            out = symbol.detailed_description
            f.write (out.encode('utf-8'))

    def __format_doc_string (self, docstring):
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
            out += self.__format_doc_string (comment.description)
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
