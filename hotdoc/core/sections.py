# -*- coding: utf-8 -*-

from .symbols import *
from .links import Link

class TypedSymbolsList (object):
    def __init__ (self, name):
        self.name = name
        self.symbols = []

class Page:
    def __init__(self, name):
        self.symbols = []
        self.subpages = []
        pagename = '%s.html' % name
        self.link = Link (pagename, name, name) 

        self.formatted_contents = None
        self.formatted_doc = ''

        self.typed_symbols = {}
        self.typed_symbols[FunctionSymbol] = TypedSymbolsList ("Functions")
        self.typed_symbols[CallbackSymbol] = TypedSymbolsList ("Callback Functions")
        self.typed_symbols[FunctionMacroSymbol] = TypedSymbolsList ("Function Macros")
        self.typed_symbols[ConstantSymbol] = TypedSymbolsList ("Constants")
        self.typed_symbols[ExportedVariableSymbol] = TypedSymbolsList ("Exported Variables")
        self.typed_symbols[StructSymbol] = TypedSymbolsList ("Data Structures")
        self.typed_symbols[EnumSymbol] = TypedSymbolsList ("Enumerations")
        self.typed_symbols[AliasSymbol] = TypedSymbolsList ("Aliases")
        self.typed_symbols[SignalSymbol] = TypedSymbolsList ("Signals")
        self.typed_symbols[PropertySymbol] = TypedSymbolsList ("Properties")
        self.typed_symbols[VFunctionSymbol] = TypedSymbolsList ("Virtual Methods")
        self.typed_symbols[ClassSymbol] = TypedSymbolsList ("Classes")

        self.ast = None
        self.short_description = ''
        self.title = ''

    def add_symbol (self, symbol):
        symbol.link.ref = '%s#%s' % (self.link.ref, symbol.link.ref)
        for l in symbol.get_extra_links():
            l.ref = '%s#%s' % (self.link.ref, l.ref)
        tsl = self.typed_symbols[type(symbol)]
        tsl.symbols.append (symbol)
        self.symbols.append (symbol)
        if type (symbol) == ClassSymbol and symbol.comment:
            if symbol.comment.short_description:
                self.short_description = symbol.comment.short_description
            if symbol.comment.title:
                self.title = symbol.comment.title

    def get_short_description (self):
        return self.short_description

    def get_title (self):
        return self.title

    def format_symbols (self):
        for type_, tsl in self.typed_symbols.iteritems():
            for symbol in tsl.symbols:
                symbol.do_format ()
