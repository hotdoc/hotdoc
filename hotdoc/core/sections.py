# -*- coding: utf-8 -*-

from .symbols import *
from .links import Link

class TypedSymbolsList (object):
    def __init__ (self, name):
        self.name = name
        self.symbols = []

class Page(object):
    def __init__(self, name, source_file, extension_name):
        self.symbols = []
        self.symbol_names = []
        self.subpages = []
        pagename = '%s.html' % name
        self.link = Link (pagename, name, name) 
        self.source_file = source_file
        self.extension_name = extension_name
        self.parsed_page = None
        self.short_description = ''
        self.title = ''

    def __getstate__(self):
        return {'symbol_names': self.symbol_names,
                'subpages': self.subpages,
                'link': self.link,
                'title': self.title,
                'short_description': self.short_description,
                'source_file': self.source_file,
                'extension_name': self.extension_name}

    def add_symbol (self, symbol_name):
        self.symbol_names.append (symbol_name)

    def resolve_symbols (self, doc_tool):
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

        self.formatted_contents = None
        self.formatted_doc = ''

        for sym_name in self.symbol_names:
            sym = doc_tool.get_symbol(sym_name)
            if sym:
                self.resolve_symbol (sym)

            new_symbols = sum(doc_tool.page_parser.symbol_added_signal(self, sym), [])
            for symbol in new_symbols:
                self.resolve_symbol (symbol)

    def resolve_symbol (self, symbol):
        if not '#' in symbol.link.ref:
            symbol.link.ref = '%s#%s' % (self.link.ref, symbol.link.ref)
        for l in symbol.get_extra_links():
            if not '#' in l.ref:
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
