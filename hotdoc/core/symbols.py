# -*- coding: utf-8 -*-

import os
import re
import linecache
import uuid

from .links import Link
from ..utils.simple_signals import Signal
from ..utils.utils import all_subclasses
from .doc_tool import doc_tool

import sqlalchemy
from sqlalchemy import (create_engine, Column, String, Integer, Boolean,
        ForeignKey, PickleType)
from sqlalchemy.orm import relationship
from hotdoc.core.alchemy_integration import *

def get_symbol(name):
    return session.query(Symbol).filter(Symbol.name == name).first()

def get_or_create_symbol(type_, **kwargs):
    name = kwargs.pop('name')
    filename = kwargs.get('filename')
    if filename:
        kwargs['filename'] = os.path.abspath(filename)

    symbol = session.query(type_).filter(type_.name == name).first()
    if not symbol:
        symbol = type_(name=name)

    for key, value in kwargs.items():
        setattr(symbol, key, value)

    return symbol

class Symbol (Base):
    __tablename__ = 'symbols'

    id = Column(Integer, primary_key=True)
    comment = Column(PickleType)
    name = Column(String)
    link = Column(Link.as_mutable(PickleType))
    filename = Column(String)
    lineno = Column(Integer)
    location = Column(PickleType)
    _type_ = Column(String)
    extension_contents = Column(MutableDict.as_mutable(PickleType))
    extension_attributes = Column(MutableDict.as_mutable(PickleType))
    skip = Column(Boolean)

    __mapper_args__ = {
            'polymorphic_identity': 'symbol',
            'polymorphic_on': _type_,
    }

    def __init__(self, **kwargs):
        self.extension_contents = {}
        self.extension_attributes = {}
        self.name = kwargs.get('name')
        self.skip = False
        link = Link(self._make_unique_id(), self._make_name(),
                    self._make_unique_id())
        link = doc_tool.link_resolver.upsert_link(link)

        kwargs['link'] = link

        Base.__init__(self, **kwargs)

    def add_extension_attribute (self, ext_name, key, value):
        attributes = self.extension_attributes.pop (ext_name, {})
        attributes[key] = value
        self.extension_attributes[ext_name] = attributes

    def get_extension_attribute (self, ext_name, key):
        attributes = self.extension_attributes.get (ext_name)
        if not attributes:
            return None
        return attributes.get (key)

    def get_children_symbols (self):
        return []

    def _make_name (self):
        return self.name

    def _make_unique_id (self):
        return self.name

    def get_extra_links (self):
        return []

    def get_type_name (self):
        return ''

    def get_source_location (self):
        return self.location

class Tag:
    def __init__(self, name, value):
        self.name = name
        self.description = value

class FunctionSymbol (Symbol):
    __tablename__ = 'functions'
    id = Column(Integer, ForeignKey('symbols.id'), primary_key=True)
    parameters = Column(MutableList.as_mutable(PickleType))
    return_value = Column(PickleType)
    is_method = Column(Boolean)
    throws = Column(Boolean)
    __mapper_args__ = {
            'polymorphic_identity': 'functions',
    }

    def __init__(self, **kwargs):
        self.parameters = []
        self.throws = False
        self.is_method = False
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.parameters + [self.return_value]

    def get_type_name (self):
        if self.is_method:
            return 'Method'
        return 'Function'

class SignalSymbol (FunctionSymbol):
    __tablename__ = 'signals'
    id = Column(Integer, ForeignKey('functions.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'signals',
    }
    object_name = Column(String)
    flags = Column(PickleType)

    def __init__(self, **kwargs):
        self.flags = []
        FunctionSymbol.__init__(self, **kwargs)

    def get_type_name (self):
        return "Signal"

    def _make_unique_id (self):
        return '%s:::%s---signal' % (self.object_name, self.name)

class VFunctionSymbol (FunctionSymbol):
    __tablename__ = 'vfunctions'
    id = Column(Integer, ForeignKey('functions.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'vfunctions',
    }
    object_name = Column(String)
    flags = Column(PickleType)

    def __init__(self, **kwargs):
        self.flags = []
        FunctionSymbol.__init__(self, **kwargs)

    def get_type_name (self):
        return "Virtual Method"

    def _make_unique_id (self):
        return '%s:::%s---vfunc' % (self.object_name, self.name)

class PropertySymbol (Symbol):
    __tablename__ = 'properties'
    id = Column(Integer, ForeignKey('symbols.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'properties',
    }
    object_name = Column(String)
    prop_type = Column(PickleType)

    def _make_unique_id (self):
        return '%s:::%s---property' % (self.object_name, self.name)

class CallbackSymbol (FunctionSymbol):
    __tablename__ = 'callbacks'
    id = Column(Integer, ForeignKey('functions.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'callbacks',
    }

    def get_type_name (self):
        return "Callback"

class EnumSymbol (Symbol):
    __tablename__ = 'enums'
    id = Column(Integer, ForeignKey('symbols.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'enums',
    }
    members = Column(PickleType)

    def __init__(self, **kwargs):
        self.members = {}
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.members

    def get_extra_links (self):
        return [m.link for m in self.members]

    def get_type_name (self):
        return "Enumeration"

class StructSymbol (Symbol):
    __tablename__ = 'structs'
    id = Column(Integer, ForeignKey('symbols.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'structs',
    }
    members = Column(PickleType)
    raw_text = Column(String)

    def __init__(self, **kwargs):
        self.members = {}
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.members

    def get_type_name (self):
        return "Structure"

    def _make_unique_id (self):
        return self.name + "-struct"

class MacroSymbol (Symbol):
    __tablename__ = 'macros'
    id = Column(Integer, ForeignKey('symbols.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'macros',
    }
    original_text = Column(String)

class FunctionMacroSymbol (MacroSymbol):
    __tablename__ = 'function_macros'
    id = Column(Integer, ForeignKey('macros.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'function_macros',
    }

    parameters = Column(MutableList.as_mutable(PickleType))
    return_value = Column(PickleType)

    def __init__(self, **kwargs):
        self.parameters = []
        MacroSymbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.parameters + [self.return_value]

    def get_type_name (self):
        return "Function macro"

class ConstantSymbol (MacroSymbol):
    __tablename__ = 'constants'
    id = Column(Integer, ForeignKey('macros.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'constants',
    }

    def get_type_name (self):
        return "Constant"


class ExportedVariableSymbol (MacroSymbol):
    __tablename__ = 'exported_variables'
    id = Column(Integer, ForeignKey('macros.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'exported_variables',
    }

    def get_type_name (self):
        return "Exported variable"

class QualifiedSymbol (MutableObject):
    def __init__(self, type_tokens=[]):
        self.type_tokens = type_tokens
        self.type_link = None

        for tok in self.type_tokens:
            if isinstance(tok, Link):
                self.type_link = tok
                break

        self.extension_contents = {}
        self.extension_attributes = {}
        MutableObject.__init__(self)

    def add_extension_attribute (self, ext_name, key, value):
        attributes = self.extension_attributes.pop (ext_name, {})
        attributes[key] = value
        self.extension_attributes[ext_name] = attributes

    def get_extension_attribute (self, ext_name, key):
        attributes = self.extension_attributes.get (ext_name)
        if not attributes:
            return None
        return attributes.get (key)

    def get_children_symbols(self):
        return []

    def get_type_link (self):
        return self.type_link

class ReturnValueSymbol (QualifiedSymbol):
    def __init__(self, comment=None, **kwargs):
        self.comment = comment
        QualifiedSymbol.__init__(self, **kwargs)

class ParameterSymbol (QualifiedSymbol):
    def __init__(self, argname='', comment=None, **kwargs):
        QualifiedSymbol.__init__(self, **kwargs)
        self.array_nesting = 0
        self.argname = argname
        self.comment = comment

class FieldSymbol (QualifiedSymbol):
    def __init__(self, member_name='', is_function_pointer=False,
            comment=None, **kwargs):
        QualifiedSymbol.__init__(self, **kwargs)
        self.member_name = member_name
        self.is_function_pointer = is_function_pointer
        self.comment = comment
        link = Link(self.member_name, self.member_name,
                    self.member_name)
        link = doc_tool.link_resolver.upsert_link(link)

        self.link = link

    def _make_name (self):
        return self.member_name

    def get_type_name (self):
        return "Attribute"

class AliasSymbol (Symbol):
    __tablename__ = 'aliases'
    id = Column(Integer, ForeignKey('symbols.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'aliases',
    }
    aliased_type = Column(PickleType)

    def get_type_name (self):
        return "Alias"


class ClassSymbol (Symbol):
    __tablename__ = 'classes'
    id = Column(Integer, ForeignKey('symbols.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'classes',
    }
    hierarchy = Column(PickleType)
    children = Column(PickleType)

    def get_type_name (self):
        return "Class"

Base.metadata.create_all(engine)
