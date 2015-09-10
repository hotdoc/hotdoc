# -*- coding: utf-8 -*-

import os
from .doc_tool import doc_tool
from ..utils.loggable import Loggable

class ParsedPage(object):
    def __init__(self):
        self.ast = None
        self.headers = []

class PageParser(Loggable):
    def __init__(self):
        Loggable.__init__(self)
        self.sections = []
        self._current_section = None
        self.__parsed_pages = []
        self._prefix = ""
        self.__total_documented_symbols = 0
        self.create_object_hierarchy = False
        self.create_api_index = False

    def create_section (self, section_name, filename):
        comment = doc_tool.comments.get("SECTION:%s" % section_name.lower())
        symbol = doc_tool.source_scanner.symbols.get(section_name)
        if not symbol:
            symbol = section_name
        section = doc_tool.symbol_factory.make_section (symbol, comment)
        section.source_file = filename
        section.link.pagename = "%s.%s" % (section_name, "html")

        if self._current_section:
            self._current_section.sections.append (section)
        else:
            self.sections.append (section)

        self._current_section = section

    def create_section_from_well_known_name (self, section_name):
        if section_name.lower() == 'object hierarchy':
            self.create_object_hierarchy = True
            return 'object_hierarchy.html'
        elif section_name.lower() == 'api index':
            self.create_api_index = True
            return 'api_index.html'
        return ''

    def create_symbol (self, symbol_name):
        if not self._current_section:
            return

        symbol = doc_tool.source_scanner.symbols.get (symbol_name)
        if symbol:
            comment_block = doc_tool.comments.get (symbol_name)
            if comment_block:
                sym = doc_tool.symbol_factory.make (symbol,
                        comment_block)
                if sym:
                    self._current_section.add_symbol (sym)
                    self.__total_documented_symbols += 1
            else:
                self.warning ("No comment in sources for symbol with name %s", symbol_name)
        else:
            self.warning ("No symbol in sources with name %s", symbol_name)

    def __update_dependencies (self, sections):
        for s in sections:
            if not s.symbols:
                doc_tool.dependency_tree.add_dependency (s.source_file,
                        None)
            for sym in s.symbols:
                if not hasattr (sym._symbol, "location"):
                    continue

                filename = str (sym._symbol.location.file)
                doc_tool.dependency_tree.add_dependency (s.source_file, filename)
                comment_filename = sym.comment.filename
                doc_tool.dependency_tree.add_dependency (s.source_file, comment_filename)

            self.__update_dependencies (s.sections)

    def _parse_page (self, filename, section_name):
        filename = os.path.abspath (filename)
        if not os.path.isfile (filename):
            return None

        if filename in self.__parsed_pages:
            return None

        self.__parsed_pages.append (filename)
        self.create_section (section_name, filename)

        with open (filename, "r") as f:
            contents = f.read()

        old_section = self._current_section
        old_section.parsed_page = self.do_parse_page (contents, self._current_section)

        return old_section

    def create_symbols(self):
        self._prefix = os.path.dirname (doc_tool.index_file)
        if doc_tool.dependency_tree.initial:
            self._parse_page (doc_tool.index_file, "index")
        else:
            for filename in doc_tool.dependency_tree.stale_sections:
                section_name = os.path.splitext(os.path.basename (filename))[0]
                self._parse_page (filename, section_name)
        self.__update_dependencies (self.sections)
        self.info ("total documented symbols : %d" %
                self.__total_documented_symbols)
