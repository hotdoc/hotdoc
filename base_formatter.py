# -*- coding: utf-8 -*-

import os
import json
import logging

from gnome_markdown_filter import GnomeMarkdownFilter

from datetime import datetime
from xml.sax.saxutils import unescape

from pandoc_client import pandoc_converter

import clang.cindex

from sections import SectionFilter
from symbols import SymbolFactory
from links import ExternalLinkResolver


class Annotation (object):
    def __init__(self, nick, help_text):
        self.nick = nick
        self.help_text = help_text


class Flag (object):
    def __init__ (self, nick, link):
        self.nick = nick
        self.link = link


class RunLastFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Run Last",
                "https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-RUN-LAST:CAPS")


class RunFirstFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Run First",
                "https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-RUN-FIRST:CAPS")


class RunCleanupFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Run Cleanup",
                "https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-RUN-CLEANUP:CAPS")


class WritableFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Write", None)


class ReadableFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Read", None)


class ConstructFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Construct", None)


class ConstructOnlyFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Construct Only", None)


class Formatter(object):
    def __init__ (self, symbols, external_symbols, comments, include_directories, index_file, output,
            extensions, do_class_aggregation=False):
        self.__include_directories = include_directories
        self.__do_class_aggregation = do_class_aggregation
        self.__output = output
        self.__index_file = index_file
        self.__symbols = symbols
        self.__external_symbols = external_symbols
        self.__comments = comments

        self.__link_resolver = ExternalLinkResolver ()
        self.__symbol_factory = SymbolFactory (self, extensions, comments)
        self.__local_links = {}
        self.__gnome_markdown_filter = GnomeMarkdownFilter (os.path.dirname(index_file))
        self.__gnome_markdown_filter.set_formatter (self)

        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}

    def lookup_ast_node (self, name):
        return self.__symbols.get(name) or self.__external_symbols.get(name)

    def lookup_underlying_type (self, name):
        ast_node = self.lookup_ast_node (name)
        if not ast_node:
            return None

        while ast_node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            t = ast_node.underlying_typedef_type
            ast_node = t.get_declaration()
        return ast_node.kind

    def create_symbols(self):
        n = datetime.now()
        sf = SectionFilter (os.path.dirname(self.__index_file), self.__symbols,
                self.__comments, self, self.__symbol_factory)
        sf.create_symbols (os.path.basename(self.__index_file))
        self.__local_links = sf.local_links
        print "Markdown parsing done", datetime.now() - n
        return sf.sections

    def __format_section (self, section):
        out = ""
        section.do_format ()
        #with open (os.path.join (self.__output, filename), 'w') as f:
        #    if section.parsed_contents and not section.ast_node:
        #        out += pandoc_converter.convert("json", "html", json.dumps
        #                (section.parsed_contents))
            #out += self._format_class (section, True)
        #    section.filename = os.path.basename(filename)
            #f.write (out.encode('utf-8'))

        for section in section.sections:
            self.__format_section (section)

    def write_symbol (self, symbol):
        path = os.path.join (self.__output, symbol.link.pagename)
        with open (path, 'w') as f:
            f.write (symbol.detailed_description.encode('utf-8'))

    def format (self):
        n = datetime.now ()
        sections = self.create_symbols ()

        for section in sections:
            self.__format_section (section)

    def get_named_link(self, ident, search_remote=True):
        link = None
        try:
            link = self.__local_links [ident]
        except KeyError:
            if search_remote:
                link = self.__link_resolver.get_named_link (ident)
        return link

    def __format_doc_string (self, docstring):
        if not docstring:
            return ""

        out = ""
        docstring = unescape (docstring)
        json_doc = self.__gnome_markdown_filter.filter_text (docstring)
        html_text = pandoc_converter.convert ("json", "html", json.dumps (json_doc))
        return html_text

    def format_doc (self, comment):
        out = ""
        if comment:
            out += self.__format_doc_string (comment.description)
        return out

    def __warn_not_implemented (self, func):
        if func in self.__not_implemented_methods:
            return
        self.__not_implemented_methods [func] = True
        logging.warning ("%s not implemented !" % func) 

    # Virtual methods

    def _get_extension (self):
        """
        The extension to append to the filename
        ('markdown', 'html')
        """
        self.__warn_not_implemented (self._get_extension)
        return ""
