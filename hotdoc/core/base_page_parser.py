# -*- coding: utf-8 -*-

import os
from .sections import Page
from ..utils.loggable import Loggable
from ..utils.simple_signals import Signal
from hotdoc.core.doc_tool import doc_tool

class ParsedPage(object):
    def __init__(self):
        self.ast = None
        self.headers = []
        self.links = []

class PageParser(Loggable):
    def __init__(self):
        Loggable.__init__(self)
        self.pages = []
        self._current_page = None
        self.__parsed_pages = {}
        self._prefix = ""
        self.__total_documented_symbols = 0
        self.create_object_hierarchy = False
        self.create_api_index = False
        self.symbol_added_signal = Signal()

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

        sym = doc_tool.get_symbol (symbol_name)
        if sym:
            self._current_page.add_symbol (sym)
            self.__total_documented_symbols += 1
            new_symbols = sum(self.symbol_added_signal (sym), [])
            for symbol in new_symbols:
                self._current_page.add_symbol (symbol)
                self.__total_documented_symbols += 1
        else:
            self.warning ("No symbol in sources with name %s", symbol_name)

    def _parse_page (self, filename):
        filename = os.path.abspath (filename)
        page_name = os.path.splitext(os.path.basename (filename))[0]
        if not os.path.isfile (filename):
            return None

        if filename in self.__parsed_pages:
            return self.__parsed_pages[filename]

        old_page = self._current_page

        self.create_page (page_name, filename)

        with open (filename, "r") as f:
            contents = f.read()

        cur_page = self._current_page
        cur_page.parsed_page = self.do_parse_page (contents, self._current_page)

        self._current_page = old_page

        self.__parsed_pages[filename] = cur_page
        return cur_page

    def create_symbols(self, doc_tool):
        if not os.path.isfile (doc_tool.index_file):
            raise IOError ('Index file %s not found' % doc_tool.index_file)

        self._prefix = os.path.dirname (doc_tool.index_file)
        self._parse_page (doc_tool.index_file)
        self.info ("total documented symbols : %d" %
                self.__total_documented_symbols)
