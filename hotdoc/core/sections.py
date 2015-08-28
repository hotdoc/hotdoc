# -*- coding: utf-8 -*-

from .symbols import *

class TypedSymbolsList (object):
    def __init__ (self, name):
        self.name = name
        self.symbols = []


class SectionSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__ (self, *args)
        self.symbols = []
        self.sections = []

        self.typed_symbols = {}
        self.typed_symbols[FunctionSymbol] = TypedSymbolsList ("Functions")
        self.typed_symbols[CallbackSymbol] = TypedSymbolsList ("Callback Functions")
        self.typed_symbols[FunctionMacroSymbol] = TypedSymbolsList ("Function Macros")
        self.typed_symbols[ConstantSymbol] = TypedSymbolsList ("Constants")
        self.typed_symbols[ExportedVariableSymbol] = TypedSymbolsList ("Exported Variables")
        self.typed_symbols[StructSymbol] = TypedSymbolsList ("Data Structures")
        self.typed_symbols[EnumSymbol] = TypedSymbolsList ("Enumerations")
        self.typed_symbols[AliasSymbol] = TypedSymbolsList ("Aliases")
        self.ast = None
        self.formatted_contents = None
        if self.comment is not None and self.comment.title is not None:
            self.link.title = self.comment.title

    def _register_typed_symbol (self, symbol_type, symbol_type_name):
        self.typed_symbols[symbol_type] = TypedSymbolsList (symbol_type_name)

    def do_format (self):
        # Reset at each run
        for symbol_type, tsl in self.typed_symbols.iteritems():
            tsl.symbols = []

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
        if not self.comment:
            return ""
        if not self.comment.short_description:
            return ""
        return self.comment.short_description

    def get_title (self):
        if not self.comment:
            return ""
        if not self.comment.title:
            return ""
        return self.comment.title
