# -*- coding: utf-8 -*-

import os
from .sections import Page
from ..utils.loggable import Loggable
from ..utils.simple_signals import Signal

class ParsedPage(object):
    def __init__(self):
        self.ast = None
        self.headers = []

class PageParser(Loggable):
    def __init__(self):
        Loggable.__init__(self)
        self.pages = []
        self._current_page = None
        self.__parsed_pages = []
        self._prefix = ""
        self.__total_documented_symbols = 0
        self.create_object_hierarchy = False
        self.create_api_index = False
        self.symbol_added_signal = Signal()
        self.doc_tool = None

    def create_page (self, page_name, filename):
        page = Page (page_name)
        page.source_file = filename

        if self._current_page:
            self._current_page.subpages.append (page)
        else:
            self.pages.append (page)

        self._current_page = page

    def create_page_from_well_known_name (self, page_name):
        if page_name.lower() == 'object hierarchy':
            self.create_object_hierarchy = True
            return 'object_hierarchy.html'
        elif page_name.lower() == 'api index':
            self.create_api_index = True
            return 'api_index.html'
        return ''

    def create_symbol (self, symbol_name):
        if not self._current_page:
            return

        sym = self.doc_tool.get_symbol (symbol_name)
        if sym:
            self._current_page.add_symbol (sym)
            self.__total_documented_symbols += 1
            new_symbols = sum(self.symbol_added_signal (sym), [])
            for symbol in new_symbols:
                self._current_page.add_symbol (symbol)
                self.__total_documented_symbols += 1
        else:
            self.warning ("No symbol in sources with name %s", symbol_name)

    def __update_dependencies (self, pages):
        for s in pages:
            if not s.symbols:
                self.doc_tool.dependency_tree.add_dependency (s.source_file,
                        None)
            for sym in s.symbols:
                location = sym.get_source_location()
                if location is None:
                    continue

                filename = str (location.file)
                self.doc_tool.dependency_tree.add_dependency (s.source_file,
                        filename)
                if sym.comment:
                    comment_filename = sym.comment.filename
                    self.doc_tool.dependency_tree.add_dependency (s.source_file, comment_filename)

            self.__update_dependencies (s.subpages)

    def _parse_page (self, filename, page_name):
        filename = os.path.abspath (filename)
        if not os.path.isfile (filename):
            return None

        if filename in self.__parsed_pages:
            return None

        self.__parsed_pages.append (filename)
        self.create_page (page_name, filename)

        with open (filename, "r") as f:
            contents = f.read()

        old_page = self._current_page
        old_page.parsed_page = self.do_parse_page (contents, self._current_page)

        return old_page

    def create_symbols(self, doc_tool):
        self.doc_tool = doc_tool
        self._prefix = os.path.dirname (doc_tool.index_file)
        if doc_tool.dependency_tree.initial:
            self._parse_page (doc_tool.index_file, "index")
        else:
            for filename in doc_tool.dependency_tree.stale_sections:
                page_name = os.path.splitext(os.path.basename (filename))[0]
                self._parse_page (filename, page_name)
        self.__update_dependencies (self.pages)
        self.info ("total documented symbols : %d" %
                self.__total_documented_symbols)
