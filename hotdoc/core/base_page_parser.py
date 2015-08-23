# -*- coding: utf-8 -*-

import os
import CommonMark

from .doc_tool import doc_tool

class PageParser:
    def __init__(self):
        self.__cmp = CommonMark.DocParser()
        self.__cmr = CommonMark.HTMLRenderer()
        self.__prefix = ""
        self.__current_section = None
        self.__parsed_pages = []
        self.sections = []
        self.__labels_to_rename = {}

    def create_symbol (self, symbol_name):
        symbol = doc_tool.source_scanner.symbols.get (symbol_name)
        if symbol:
            comment_block = doc_tool.comments.get (symbol_name)
            if comment_block:
                sym = doc_tool.symbol_factory.make (symbol,
                        comment_block)
                if sym:
                    self.__current_section.add_symbol (sym)

    def parse_list (self, l):
        for c in l.children:
            for c2 in c.children:
                if c2.t == "Paragraph" and len (c2.inline_content) == 1:
                    self.parse_para (c2.inline_content[0])

    def parse_para(self, ic):
        if ic.t != "Link":
            return
        if not ic.destination and ic.label:
            l = ''.join ([l.c for l in ic.label])
            self.create_symbol (l)

    def parse_header(self, h):
        ic = h.inline_content[0]
        if ic.t != "Link":
            return

        section_name = ''.join ([l.c for l in ic.label])
        filename = os.path.join (self.__prefix, ic.destination)

        old_section = self.__current_section
        self.parse_page (filename, section_name)
        if self.__current_section != old_section:
            ic.destination = self.__current_section.link.pagename
            desc = self.__current_section.get_short_description()
            if desc:
                s = CommonMark.CommonMark.Block.makeBlock ("Str", "", "")
                desc = u' — %s' % desc
                s.c = desc
                h.inline_content.append (s)

            title = self.__current_section.get_title()
            if title:
                ic.label[0].c = title
            else:
                try:
                    labels_to_rename = self.__labels_to_rename[old_section.link.id_]
                except KeyError:
                    labels_to_rename = []
                    self.__labels_to_rename[old_section.link.id_] = labels_to_rename
                labels_to_rename.append(ic.label[0])
                ic.label[0].original_name = ic.label[0].c

        self.__current_section = old_section

    def create_section (self, section_name, filename):
        comment = doc_tool.comments.get("SECTION:%s" % section_name.lower())
        symbol = doc_tool.source_scanner.symbols.get(section_name)
        if not symbol:
            symbol = section_name
        section = doc_tool.symbol_factory.make_section (symbol, comment)
        section.source_file = filename
        section.link.pagename = "%s.%s" % (section_name, "html")

        if self.__current_section:
            self.__current_section.sections.append (section)
        else:
            self.sections.append (section)
        self.__current_section = section

    def parse_page(self, filename, section_name):
        filename = os.path.abspath (filename)
        if not os.path.isfile (filename):
            return False

        if filename in self.__parsed_pages:
            return

        self.__parsed_pages.append (filename)
        self.create_section (section_name, filename)

        with open (filename, "r") as f:
            ct = f.read()

        ast = self.__cmp.parse (ct)
        for c in ast.children:
            if c.t == "List":
                self.parse_list(c)
            elif c.t == "ATXHeader" and len (c.inline_content) == 1:
                self.parse_header (c)

        if not self.__current_section.symbols:
            self.__current_section.ast = ast

    def render_ast (self, ast):
        return self.__cmr.render (ast)

    def rename_labels(self, klass, names):
        labels = self.__labels_to_rename.get(klass.link.id_)
        if not labels:
            return

        for l in labels:
            new_name = names.get(l.original_name)
            if new_name:
                l.c = new_name

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

    def create_symbols(self):
        self.__prefix = os.path.dirname (doc_tool.index_file)
        if doc_tool.dependency_tree.initial:
            self.parse_page (doc_tool.index_file, "index")
        else:
            for filename in doc_tool.dependency_tree.stale_sections:
                section_name = os.path.splitext(os.path.basename (filename))[0]
                self.parse_page (filename, section_name)
        self.__update_dependencies (self.sections)
