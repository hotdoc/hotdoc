# -*- coding: utf-8 -*-

import re
import linecache
import uuid

from .links import LocalLink, Link
from ..utils.simple_signals import Signal
from ..utils.utils import all_subclasses
from .doc_tool import doc_tool

class Symbol (object):
    def __init__(self, comment, name, location):
        from hotdoc.core.doc_tool import doc_tool
        self.comment = comment
        self.name = name
        self.original_text = None
        self.detailed_description = None
        self.link = doc_tool.link_resolver.get_named_link (self._make_unique_id())
        if not self.link:
            self.link = LocalLink (self._make_unique_id(), "", self._make_name())

        doc_tool.link_resolver.add_local_link (self.link)
        self.location = location

    def parse_tags(self):
        if not self.comment:
            return []

        if not hasattr (self.comment, "tags"):
            return []

        tags = []
        for tag, value in self.comment.tags.iteritems():
            tags.append (Tag (tag, value.value))
        return tags

    def do_format (self):
        from hotdoc.core.doc_tool import doc_tool
        self.tags = self.parse_tags ()
        return doc_tool.formatter.format_symbol (self)

    def _make_name (self):
        return self.name

    def _make_unique_id (self):
        return self.name

    def get_extra_links (self):
        return []

    def add_annotation (self, annotation):
        self.annotations.append (annotation)

    def get_type_name (self):
        return ''

    def __apply_qualifiers (self, type_, tokens):
        if type_.is_const_qualified():
            tokens.append ('const ')
        if type_.is_restrict_qualified():
            tokens.append ('restrict ')
        if type_.is_volatile_qualified():
            tokens.append ('volatile ')

    def get_source_location (self):
        return self.location

class Tag:
    def __init__(self, name, value):
        self.name = name
        self.description = value

class FunctionSymbol (Symbol):
    def __init__(self, parameters, return_value, *args):
        Symbol.__init__(self, *args)
        self.parameters = parameters
        self.return_value = return_value
        self.throws = False
        self.is_method = False

    def get_type_name (self):
        if self.is_method:
            return 'Method'
        return 'Function'

class SignalSymbol (FunctionSymbol):
    def __init__(self, object_name, *args):
        self.object_name = object_name
        FunctionSymbol.__init__(self, *args)
        self.flags = []

    def get_type_name (self):
        return "Signal"

    def _make_unique_id (self):
        return '%s:::%s---signal' % (self.object_name, self.name)

class VFunctionSymbol (FunctionSymbol):
    def __init__(self, object_name, *args):
        self.object_name = object_name
        FunctionSymbol.__init__(self, *args)
        self.flags = []

    def get_type_name (self):
        return "Virtual Method"

    def _make_unique_id (self):
        return '%s:::%s---vfunc' % (self.object_name, self.name)

class PropertySymbol (Symbol):
    def __init__(self, type_, object_name, comment, name):
        self.object_name = object_name
        self.type_ = type_
        self.flags = []
        Symbol.__init__(self, comment, name, None)

    def _make_unique_id (self):
        return '%s:::%s---property' % (self.object_name, self.name)

class CallbackSymbol (FunctionSymbol):
    pass

    def get_type_name (self):
        return "Callback"

class EnumSymbol (Symbol):
    def __init__(self, members, *args):
        Symbol.__init__(self, *args)
        self.members = members

    def get_extra_links (self):
        return [m.link for m in self.members]

    def get_type_name (self):
        return "Enumeration"

class StructSymbol (Symbol):
    def __init__(self, raw_text, members, *args):
        Symbol.__init__(self, *args)
        self.raw_text = raw_text
        self.members = members

    def get_type_name (self):
        return "Structure"

    def _make_unique_id (self):
        return self.name + "-struct"

class MacroSymbol (Symbol):
    def __init__(self, original_text, *args):
        Symbol.__init__(self, *args)
        self.original_text = original_text

class FunctionMacroSymbol (MacroSymbol):
    def __init__(self, return_value, parameters, *args):
        MacroSymbol.__init__(self, *args)
        self.return_value = return_value
        self.parameters = parameters

    def get_type_name (self):
        return "Function macro"

class ConstantSymbol (MacroSymbol):
    def get_type_name (self):
        return "Constant"


class ExportedVariableSymbol (MacroSymbol):
    def get_type_name (self):
        return "Exported variable"

class QualifiedSymbol (Symbol):
    def __init__(self, type_tokens, comment):
        Symbol.__init__(self, comment, None, None)
        self.type_tokens = type_tokens

    def get_type_link (self):
        for tok in self.type_tokens:
            if isinstance(tok, Link):
                return tok
        return None

class ReturnValueSymbol (QualifiedSymbol):
    pass

class ParameterSymbol (QualifiedSymbol):
    def __init__(self, argname, *args):
        self.argname = argname
        QualifiedSymbol.__init__(self, *args)

class FieldSymbol (QualifiedSymbol):
    def __init__(self, is_function_pointer, member_name, *args):
        self.member_name = member_name
        self.is_function_pointer = is_function_pointer
        QualifiedSymbol.__init__(self, *args)

    def _make_name (self):
        return self.member_name

    def get_type_name (self):
        return "Attribute"

class AliasSymbol (Symbol):
    def __init__(self, aliased_type, *args):
        Symbol.__init__(self, *args)
        self.aliased_type = aliased_type

    def get_type_name (self):
        return "Alias"

def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in all_subclasses(s)]

class SymbolFactory (object):
    def __init__(self):
        self.symbol_subclasses = all_subclasses (Symbol)
        self.symbol_subclasses.append(Symbol)
        self.new_symbol_signals = {}
        for klass in self.symbol_subclasses:
            self.new_symbol_signals [klass] = Signal()

    def make (self, symbol, comment):
        klass = None

        if symbol.spelling in doc_tool.c_source_scanner.new_symbols:
            sym = doc_tool.c_source_scanner.new_symbols[symbol.spelling]
            return sym

        return None


class ClassSymbol (Symbol):
    def __init__(self, hierarchy, children, *args):
        Symbol.__init__(self, *args)
        self.hierarchy = hierarchy
        self.children = children

    def get_type_name (self):
        return "Class"
