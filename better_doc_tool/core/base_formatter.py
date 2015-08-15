# -*- coding: utf-8 -*-

import os
import json
import shutil

from datetime import datetime
from xml.sax.saxutils import unescape

from .gnome_markdown_filter import GnomeMarkdownFilter
from .pandoc_interface import translator
from .sections import SectionFilter
from .symbols import SymbolFactory
from ..utils.simple_signals import Signal
from ..utils.loggable import progress_bar
from ..transition_scripts.gtk_doc_translator import LegacyTranslator


class Formatter(object):
    def __init__ (self, source_scanner, comments, include_directories, index_file, output,
            extensions, dependency_tree, do_class_aggregation=False):
        self.__include_directories = include_directories
        self.__do_class_aggregation = do_class_aggregation
        self.__output = output
        self.__index_file = index_file
        self.__source_scanner = source_scanner
        self.__comments = comments

        self.__symbol_factory = SymbolFactory (self, extensions, comments,
                source_scanner)
        self.__gnome_markdown_filter = GnomeMarkdownFilter (os.path.dirname(index_file))
        self.__gnome_markdown_filter.set_formatter (self)
        self.__dependency_tree = dependency_tree
        self.__legacy_translator = LegacyTranslator ()

        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}

        self.formatting_symbol_signals = {}
        for klass in self.__symbol_factory.symbol_subclasses:
            self.formatting_symbol_signals[klass] = Signal()

        for extension in extensions:
            extension.setup (self, self.__symbol_factory)

    def format (self):
        sections = self.__create_symbols ()

        self.__total_sections = 0
        self.__total_rendered_sections = 0
        for section in sections:
            self.__total_sections += self.__get_subsections_count (section)

        self.__progress_bar = progress_bar.get_progress_bar ()
        if self.__progress_bar is not None:
            self.__progress_bar.set_header("Rendering Sections (2 / 2)")
            self.__progress_bar.clear()
            self.__update_progress ()
        
        for section in sections:
            self.__format_section (section)

        self.__copy_extra_files ()

    def __update_progress (self):
        if self.__progress_bar is None:
            return

        if self.__total_sections == 0:
            return

        percent = float (self.__total_rendered_sections) / float (self.__total_sections)
        self.__progress_bar.update (percent, "%d / %d" %
                (self.__total_rendered_sections, self.__total_sections))

    def format_symbol (self, symbol):
        self.formatting_symbol_signals[type(symbol)](symbol)
        symbol.formatted_doc = self.__format_doc (symbol._comment)
        out, standalone = self._format_symbol (symbol)
        symbol.detailed_description = out
        if standalone:
            self.__write_symbol (symbol)

    def __create_symbols(self):
        sf = SectionFilter (os.path.dirname(self.__index_file),
                self.__source_scanner.symbols, self.__comments, self,
                self.__dependency_tree, self.__symbol_factory)
        sf.create_symbols (os.path.basename(self.__index_file))
        return sf.sections

    def __get_subsections_count (self, section):
        count = 1
        for subsection in section.sections:
            count += self.__get_subsections_count (subsection)
        return count

    def __format_section (self, section):
        out = ""
        section.do_format ()
        self.__total_rendered_sections += 1
        self.__update_progress()

        for section in section.sections:
            self.__format_section (section)

    def __copy_extra_files (self):
        for f in self._get_extra_files():
            basename = os.path.basename (f)
            shutil.copy (f, os.path.join (self.__output, basename))

    def __write_symbol (self, symbol):
        path = os.path.join (self.__output, symbol.link.pagename)
        with open (path, 'w') as f:
            out = symbol.detailed_description
            f.write (out.encode('utf-8'))


    def __format_doc_string (self, docstring):
        if not docstring:
            return ""

        out = ""
        docstring = unescape (docstring)
        docstring = self.__legacy_translator.translate (docstring)
        rendered_text = translator.markdown_to_html (docstring.encode('utf-8')).decode ('utf-8')
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
