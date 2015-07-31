#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pandocfilters import walk, Str, Para
import pandocfilters
import pypandoc
import json
import sys
import re

from datetime import datetime
import os

from pandoc_interface.pandoc_client import pandoc_converter
from links import link_resolver

class GnomeMarkdownFilter(object):
    def __init__(self, directory=None):
        self.__include_pattern = re.compile(r'{{(?P<include>[^ ]*)}}')
        self.directory = directory
        self.__links = {}
        self.__formatter = None

    def filter_json (self, json_doc):
        new_doc = walk (json_doc[1], self.parse_extensions, 'md', json_doc[0])
        return [json_doc[0], new_doc]

    def parse_extensions (self, key, value, format_, meta):
        if key == "Link":
            return self.parse_link (key, value, format_, meta)
        elif key == "Para" and len (value) == 1:
            return self.parse_include (key, value, format_, meta)

        return None

    def parse_link (self, key, value, format_, meta):
        if not self.__formatter:
            return None

        link = value[1]
        if not link[0] or link[0] in ['signal', 'property']:
            linkname = value[0][0]['c']
            actual_link = link_resolver.get_named_link (linkname)
            if actual_link:
                link[0] = actual_link.get_link()
        return None

    def parse_include (self, key, value, format_, meta):
        val = value[0]
        if val['t'] == "Str":
            content = val['c']
            m = self.__include_pattern.match (content)
            if m:
                filename = m.groups()[0]
                if self.directory:
                    filename = os.path.join (self.directory, filename)
                if os.path.exists (filename):
                    with open (filename, 'r') as f:
                        contents = f.read()
                        new_doc = self.filter_text (contents)
                        return new_doc[1]
        return None

    def filter_text (self, text):
        json_text = pandoc_converter.convert ("markdown", "json", text)
        doc = json.loads (json_text, strict=False)
        new_doc = self.filter_json (doc)
        return new_doc

    def set_formatter (self, formatter):
        self.__formatter = formatter

if __name__ == "__main__":
    with open (sys.argv[1], 'r') as f:
        contents = f.read ()
    gmf = GnomeMarkdownFilter()

    n = datetime.now()
    new_doc = gmf.filter_text (contents)
    html = pandoc_converter.convert ("json", "html", json.dumps (new_doc))
    print html
