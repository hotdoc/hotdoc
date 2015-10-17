# -*- coding: utf-8 -*-

import os
import re
import CommonMark
from xml.sax.saxutils import unescape
from ..core.doc_tool import doc_tool
from ..core.base_page_parser import PageParser, ParsedPage

class CommonMarkParser (PageParser):
    def __init__(self):
        PageParser.__init__(self)
        self.__cmp = CommonMark.DocParser()
        self.__cmr = CommonMark.HTMLRenderer()

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
            ic.destination = "not_an_actual_link_sorry"

    def parse_header(self, h, section):
        res = None
        ic = h.inline_content

        if ic[0].t != "Link":
            return None

        link = ic[0]
        section_name = ''.join ([l.c for l in link.label])

        if not link.destination:
            link.destination = self.create_page_from_well_known_name(section_name)
            return None

        filename = os.path.join (self._prefix, link.destination)

        new_section = self._parse_page (filename)
        if new_section is not None:
            res = ic

            link.destination = new_section.link.ref
            desc = new_section.get_short_description()
            if desc:
                link.desc = desc
            else:
                link.desc = None

            title = new_section.get_title()

            if title:
                link.label[0].c = title
                link.original_name = None
            else:
                link.original_name = link.label[0].c

        return res

    def __find_included_file(self, filename):
        if os.path.isabs(filename):
            return filename

        for include_path in doc_tool.include_paths:
            fpath = os.path.join(include_path, filename)
            if os.path.exists(fpath):
                return fpath

        return filename

    def __include_content(self, contents, node, section):
        included_content = ''
        for string in node.strings:
            if re.findall("^{{.*}}$", string):
                include_path = self.__find_included_file(re.sub("{{|}}| ", "", string))
                try:
                    included_content += open(include_path, 'r').read()
                except Exception as e:
                    raise type(e)("Could not include %s in %s - include line: '%s'"
                                  " (%s)" % (include_path, section.source_file,
                                             string, e.message))

                contents = contents.replace(string, included_content)

        if included_content:
            return contents

        return None

    def do_parse_page(self, contents, section):
        parsed_page = ParsedPage()
        parsed_headers = []

        ast = self.__cmp.parse (contents)
        for c in ast.children:
            # FIXME modify the AST in place (currently changing
            # the node strings in place won't work)
            ncontent = self.__include_content(contents, c, section)
            if ncontent:
                return self.do_parse_page(ncontent, section)

            if c.t == "List":
                self.parse_list(c)
            elif c.t == "ATXHeader" and len (c.inline_content) >= 1:
                parsed_header = self.parse_header (c, section)
                if parsed_header is not None:
                    parsed_headers.append (parsed_header)

        parsed_page.ast = ast
        parsed_page.headers = parsed_headers
        return parsed_page

    def _update_links (self, node):
        if node.t == 'Link':
            link = doc_tool.link_resolver.get_named_link (node.destination)
            node.label[-1].c += ' '
            if link and link.get_link() is not None:
                node.destination = link.get_link()

        for c in node.inline_content:
            self._update_links (c)
        for c in node.children:
            self._update_links (c)

    def _update_short_descriptions (self, page):
        for h in page.headers:
            if h[0].desc:
                del h[1:]
                desc = doc_tool.doc_parser.translate (h[0].desc)
                docstring = unescape (desc)
                desc = u' — %s' % desc.encode ('utf-8')
                sub_ast = self.__cmp.parse (desc)
                for thing in sub_ast.children:
                    for other_thing in thing.inline_content:
                        h.append (other_thing)

    def render_parsed_page (self, page):
        self._update_links (page.ast)
        self._update_short_descriptions (page)
        return self.__cmr.render (page.ast) 

    def rename_headers (self, page, new_names):
        for h in page.headers:
            if h[0].original_name:
                new_name = new_names.get(h[0].original_name)
                if new_name:
                    h[0].label[0].c = new_name
