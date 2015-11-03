# -*- coding: utf-8 -*-

import os
import re
import CommonMark
from xml.sax.saxutils import unescape
from ..core.base_page_parser import PageParser, ParsedPage

class CommonMarkParser (PageParser):
    def __init__(self, doc_tool):
        PageParser.__init__(self, doc_tool)
        self.__cmp = CommonMark.DocParser()
        self.__cmr = CommonMark.HTMLRenderer()
        self.final_destinations = {}

    def parse_list (self, l):
        for c in l.children:
            for c2 in c.children:
                if c2.t == "Paragraph" and len (c2.inline_content) == 1:
                    self.parse_para (c2)

    def parse_para(self, paragraph):
        ic = paragraph.inline_content[0]

        if ic.t != "Link":
            return

        if not ic.destination and ic.label:
            name = paragraph.strings[0].strip('[]() ')
            self.add_symbol (name)
            ic.destination = "not_an_actual_link_sorry"

    def parse_header(self, h, section):
        res = None
        ic = h.inline_content

        if ic[0].t != "Link":
            return None, None

        link = ic[0]
        section_name = ''.join ([l.c for l in link.label])

        filename = os.path.join (self._prefix, link.destination)

        new_section = self._parse_page (filename)
        if new_section is not None:
            res = ic

            link.destination = new_section.link.ref
            self.final_destinations[link.destination] = True

            link.original_name = link.label[0].c

        return res, new_section

    def __find_included_file(self, filename):
        if os.path.isabs(filename):
            return filename

        for include_path in self.doc_tool.include_paths:
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

    def check_well_known_names(self, node):
        if node.t == 'Link':
            handling_extension = self.doc_tool.get_well_known_name_handler(node.destination)
            if handling_extension:
                new_contents, new_page = handling_extension.handle_well_known_name(node.destination)
                #res = handling_extension.insert_well_known_name (node.destination)
                if new_page:
                    self._current_page.subpages.append (new_page)
                    node.destination += '.%s' % self.doc_tool.output_format
                    self.final_destinations[node.destination] = True

        for c in node.inline_content:
            self.check_well_known_names (c)
        for c in node.children:
            self.check_well_known_names (c)


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
                parsed_header, new_section = self.parse_header (c, section)
                if parsed_header is not None:
                    parsed_headers.append((parsed_header, new_section))

        self.check_well_known_names (ast)

        parsed_page.ast = ast
        parsed_page.headers = parsed_headers

        return parsed_page

    def _update_links (self, node):
        if node.t == 'Link':
            if node.destination not in self.final_destinations:
                link = self.doc_tool.link_resolver.get_named_link (node.destination)
                node.label[-1].c += ' '
                if link and link.get_link() is not None:
                    node.destination = link.get_link()
                    self.final_destinations[node.destination] = True

        for c in node.inline_content:
            self._update_links (c)
        for c in node.children:
            self._update_links (c)

    def _update_short_descriptions (self, page):
        for h, new_section in page.headers:
            desc = new_section.get_short_description()
            if desc:
                del h[1:]
                desc = self.doc_tool.doc_parser.translate (desc)
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
        if not page:
            return

        for h, new_section in page.headers:
            title = new_section.get_title()
            if title:
                h[0].label[0].c = title
            else:
                new_name = new_names.get(h[0].original_name)
                if new_name:
                    h[0].label[0].c = new_name
