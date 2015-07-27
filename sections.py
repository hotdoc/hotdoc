# -*- coding: utf-8 -*-

import os
import dagger

from symbols import *
from gnome_markdown_filter import GnomeMarkdownFilter
from pandocfilters import BulletList

class Dependency (object):
    def __init__(self, filename):
        self.filename = filename
        self.deps = set({})


class TypedSymbolsList (object):
    def __init__ (self, name):
        self.name = name
        self.symbols = []


class SectionSymbol (Symbol, Dependency):
    def __init__(self, *args):
        Symbol.__init__ (self, *args)
        self.symbols = []
        self.sections = []

        self.typed_symbols = {}
        self.typed_symbols[FunctionSymbol] = TypedSymbolsList ("Functions")
        self.typed_symbols[CallbackSymbol] = TypedSymbolsList ("Callback Functions")
        self.typed_symbols[FunctionMacroSymbol] = TypedSymbolsList ("Function Macros")
        self.typed_symbols[ConstantSymbol] = TypedSymbolsList ("Constants")
        self.typed_symbols[StructSymbol] = TypedSymbolsList ("Data Structures")
        self.typed_symbols[EnumSymbol] = TypedSymbolsList ("Enumerations")
        self.typed_symbols[AliasSymbol] = TypedSymbolsList ("Aliases")
        self.parsed_contents = None

    def _register_typed_symbol (self, symbol_type, symbol_type_name):
        self.typed_symbols[symbol_type] = TypedSymbolsList (symbol_type_name)

    def do_format (self):
        for symbol in self.symbols:
            if symbol.do_format ():
                typed_symbols_list = self.typed_symbols [type (symbol)]
                typed_symbols_list.symbols.append (symbol)
        return Symbol.do_format(self)

    def add_symbol (self, symbol):
        symbol.link.pagename = self.link.pagename
        for l in symbol.get_extra_links():
            l.pagename = self.link.pagename
        self.symbols.append (symbol)

    def get_short_description (self):
        if not self._comment:
            return ""
        if not self._comment.short_description:
            return ""
        return self._comment.short_description

    def _make_unique_id (self):
        return None


class SectionFilter (GnomeMarkdownFilter):
    def __init__(self, directory, symbols, comment_blocks, doc_formatter, symbol_factory=None):
        GnomeMarkdownFilter.__init__(self, directory)
        self.sections = []
        self.dag = dagger.dagger()
        self.__current_section = None
        self.__symbols = symbols
        self.__comment_blocks = comment_blocks
        self.__symbol_factory = symbol_factory
        self.__doc_formatter = doc_formatter
        self.local_links = {}

    def parse_extensions (self, key, value, format_, meta):
        if key == "BulletList":
            res = []
            for val in value:
                content = val[0]['c'][0]
                if content['t'] == "Link":
                    symbol_name = content['c'][0][0]['c']
                    symbol = self.__symbols.get(symbol_name)

                    if symbol:
                        comment_block = self.__comment_blocks.get (symbol_name)
                        if comment_block:
                            sym = self.__symbol_factory.make (symbol,
                                    comment_block)
                            if sym:
                                self.local_links[symbol_name] = sym.link
                                self.__current_section.add_symbol (sym)
                                for l in sym.get_extra_links():
                                    self.local_links[l.title] = l
                                #self.__current_section.deps.add('"%s"' % comment_block.position.filename)
                                #self.__current_section.deps.add('"%s"' %
                                #        str(symbol.location.file))

                res.append (val)
            if res:
                return BulletList(res)
            return []

        return GnomeMarkdownFilter.parse_extensions (self, key, value, format_,
                meta)

    def parse_link (self, key, value, format_, meta):
        old_section = self.__current_section
        if self.parse_file (value[1][0], old_section):
            value[1][0] = os.path.splitext(value[1][0])[0] + ".html"
        self.__current_section = old_section

    def parse_file (self, filename, parent=None):
        path = os.path.join(self.directory, filename)
        if not os.path.isfile (path):
            return False

        name = os.path.splitext(filename)[0]

        comment = self.__comment_blocks.get("SECTION:%s" % name.lower())
        symbol = self.__symbols.get(name)
        if not symbol:
            symbol = name
        section = self.__symbol_factory.make_section (symbol, comment)

        if self.__current_section:
            self.__current_section.sections.append (section)
        else:
            self.sections.append (section)

        self.__current_section = section
        pagename = "%s.%s" % (name, "html")
        self.__current_section.link.pagename = pagename
        self.local_links[name] = self.__current_section.link

        with open (path, 'r') as f:
            contents = f.read()
            res = self.filter_text (contents)

        #self.dag.add ('"%s"' % os.path.basename(filename), list(self.__current_section.deps))
        return True

    def create_symbols (self, filename):
        self.parse_file (filename)
        self.dag.dot("dependencies.dot")
