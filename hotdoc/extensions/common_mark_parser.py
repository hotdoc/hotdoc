# -*- coding: utf-8 -*-

import os
import CommonMark
from ..core.doc_tool import doc_tool
from ..core.base_page_parser import PageParser, ParsedPage

class CommonMarkParser (PageParser):
    def __init__(self):
        PageParser.__init__(self)
        self.__cmp = CommonMark.DocParser()
        self.__cmr = CommonMark.HTMLRenderer()
        self.__labels_to_rename = {}

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

    def parse_header(self, h, section):
        res = None
        ic = h.inline_content[0]
        if ic.t != "Link":
            return None

        section_name = ''.join ([l.c for l in ic.label])

        if not ic.destination:
            ic.destination = self.create_page_from_well_known_name(section_name)
            return None

        filename = os.path.join (self._prefix, ic.destination)

        new_section = self._parse_page (filename, section_name)
        if new_section is not None:
            ic.destination = new_section.link.ref
            desc = new_section.get_short_description()
            if desc:
                s = CommonMark.CommonMark.Block.makeBlock ("Str", "", "")
                desc = u' — %s' % desc
                s.c = desc
                h.inline_content.append (s)

            title = new_section.get_title()
            if title:
                ic.label[0].c = title
            else:
                res = ic.label[0]
                ic.label[0].original_name = ic.label[0].c
        return res

    def do_parse_page(self, contents, section):
        parsed_page = ParsedPage()
        parsed_headers = []

        ast = self.__cmp.parse (contents)
        for c in ast.children:
            if c.t == "List":
                self.parse_list(c)
            elif c.t == "ATXHeader" and len (c.inline_content) == 1:
                parsed_header = self.parse_header (c, section)
                if parsed_header is not None:
                    parsed_headers.append (parsed_header)

        parsed_page.ast = ast
        parsed_page.headers = parsed_headers
        return parsed_page

    def render_parsed_page (self, page):
        return self.__cmr.render (page.ast) 

    def rename_headers (self, page, new_names):
        for h in page.headers:
            new_name = new_names.get(h.original_name)
            if new_name:
                h.c = new_name
