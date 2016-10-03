# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""
Defines the base symbols recognized by hotdoc.

Code-parsing extensions should only create symbols defined
here for the while, subclassing will be formalized in the
future.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, PickleType, String

from hotdoc.core.comment_block import comment_from_tag
from hotdoc.core.links import Link

from hotdoc.utils.alchemy_integration import (Base, MutableDict, MutableList,
                                              MutableObject)


class Symbol(Base):
    """
    The base class for all symbols, there should be no reason for
    instantiating it directly.
    """
    __tablename__ = 'symbols'

    id_ = Column(Integer, primary_key=True)
    comment = Column(PickleType)
    unique_name = Column(String)
    display_name = Column(String)
    filename = Column(String)
    lineno = Column(Integer)
    extent_start = Column(Integer)
    extent_end = Column(Integer)
    location = Column(PickleType)
    language = Column(String)
    _type_ = Column(String)
    extension_contents = Column(MutableDict.as_mutable(PickleType))
    extension_attributes = Column(MutableDict.as_mutable(PickleType))
    link = Column(Link.as_mutable(PickleType))
    skip = Column(Boolean)

    __mapper_args__ = {
        'polymorphic_identity': 'symbol',
        'polymorphic_on': _type_,
    }

    def __init__(self, **kwargs):
        self.extension_contents = {}
        self.extension_attributes = {}
        self.skip = False

        Base.__init__(self, **kwargs)

    # FIXME: this is a bit awkward to use.
    def add_extension_attribute(self, ext_name, key, value):
        """
        Banana banana
        """
        attributes = self.extension_attributes.pop(ext_name, {})
        attributes[key] = value
        self.extension_attributes[ext_name] = attributes

    def get_extension_attribute(self, ext_name, key):
        """
        Banana banana
        """
        attributes = self.extension_attributes.get(ext_name)
        if not attributes:
            return None
        return attributes.get(key)

    # pylint: disable=no-self-use
    def get_children_symbols(self):
        """
        Banana banana
        """
        return []

    # pylint: disable=unidiomatic-typecheck
    # pylint: disable=no-member
    def update_children_comments(self):
        """
        Banana banana
        """
        if self.comment is None:
            return

        for sym in self.get_children_symbols():
            if type(sym) == ParameterSymbol:
                sym.comment = self.comment.params.get(sym.argname)
            elif type(sym) == FieldSymbol:
                sym.comment = self.comment.params.get(sym.member_name)
            elif type(sym) == ReturnItemSymbol:
                tag = self.comment.tags.get('returns')
                sym.comment = comment_from_tag(tag)
            elif type(sym) == Symbol:
                sym.comment = self.comment.params.get(sym.display_name)

    def _make_name(self):
        return self.display_name

    def get_extra_links(self):
        """
        Banana banana
        """
        return []

    def get_type_name(self):
        """
        Banana banana
        """
        return ''

    def resolve_links(self, link_resolver):
        """
        Banana banana
        """
        if self.link is None:
            self.link = Link(self.unique_name, self._make_name(),
                             self.unique_name)

        self.link = link_resolver.upsert_link(self.link, overwrite_ref=True)

        for sym in self.get_children_symbols():
            if sym:
                sym.resolve_links(link_resolver)


class QualifiedSymbol(MutableObject):
    """
    Banana banana
    """
    def __init__(self, type_tokens=None):
        self.input_tokens = type_tokens or []
        self.comment = None
        self.extension_attributes = MutableDict()
        self.__constructed()
        MutableObject.__init__(self)

    def add_extension_attribute(self, ext_name, key, value):
        """
        Banana banana
        """
        attributes = self.extension_attributes.pop(ext_name, {})
        attributes[key] = value
        self.extension_attributes[ext_name] = attributes

    def get_extension_attribute(self, ext_name, key):
        """
        Banana banana
        """
        attributes = self.extension_attributes.get(ext_name)
        if not attributes:
            return None
        return attributes.get(key)

    # pylint: disable=no-self-use
    def get_children_symbols(self):
        """
        Banana banana
        """
        return []

    def get_type_link(self):
        """
        Banana banana
        """
        return self.type_link

    # pylint: disable=attribute-defined-outside-init
    def resolve_links(self, link_resolver):
        """
        Banana banana
        """
        self.type_link = None
        self.type_tokens = []

        for tok in self.input_tokens:
            if isinstance(tok, Link):
                self.type_link = link_resolver.upsert_link(tok)
                self.type_tokens.append(self.type_link)
            else:
                self.type_tokens.append(tok)

    def __constructed(self):
        self.extension_contents = {}

    def __setstate__(self, state):
        MutableObject.__setstate__(self, state)
        self.__constructed()


class ReturnItemSymbol(QualifiedSymbol):
    """
    Banana banana
    """
    def __init__(self, comment=None, name=None, **kwargs):
        QualifiedSymbol.__init__(self, **kwargs)
        self.comment = comment
        self.name = name


class ParameterSymbol(QualifiedSymbol):
    """
    Banana banana
    """
    def __init__(self, argname='', comment=None, **kwargs):
        QualifiedSymbol.__init__(self, **kwargs)
        # FIXME: gir specific
        self.array_nesting = 0
        self.argname = argname
        self.comment = comment


class FieldSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'fields'
    id_ = Column(Integer, ForeignKey('symbols.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'fields',
    }
    qtype = Column(PickleType)
    is_function_pointer = Column(Boolean)
    member_name = Column(String)

    def __init__(self, **kwargs):
        self.is_function_pointer = False
        self.qtype = None
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return [self.qtype]

    # pylint: disable=no-self-use
    def get_type_name(self):
        """
        Banana banana
        """
        return "Attribute"


class FunctionSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'functions'
    id_ = Column(Integer, ForeignKey('symbols.id_'), primary_key=True)
    parameters = Column(MutableList.as_mutable(PickleType))
    return_value = Column(MutableList.as_mutable(PickleType))
    is_method = Column(Boolean)
    is_ctor_for = Column(String)
    throws = Column(Boolean)
    __mapper_args__ = {
        'polymorphic_identity': 'functions',
    }

    def __init__(self, **kwargs):
        self.parameters = []
        self.return_value = [None]
        self.throws = False
        self.is_method = False
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.parameters + self.return_value

    def get_type_name(self):
        if self.is_method:
            return 'Method'
        return 'Function'


class SignalSymbol(FunctionSymbol):
    """
    Banana banana
    """
    __tablename__ = 'signals'
    id_ = Column(Integer, ForeignKey('functions.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'signals',
    }
    flags = Column(PickleType)

    def __init__(self, **kwargs):
        # FIXME: flags are gobject-specific
        self.flags = []
        FunctionSymbol.__init__(self, **kwargs)

    def get_type_name(self):
        return "Signal"


class VFunctionSymbol(FunctionSymbol):
    """
    Banana banana
    """
    __tablename__ = 'vfunctions'
    id_ = Column(Integer, ForeignKey('functions.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'vfunctions',
    }
    flags = Column(PickleType)

    def __init__(self, **kwargs):
        self.flags = []
        FunctionSymbol.__init__(self, **kwargs)

    def get_type_name(self):
        return "Virtual Method"


class PropertySymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'properties'
    id_ = Column(Integer, ForeignKey('symbols.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'properties',
    }
    prop_type = Column(PickleType)

    def get_children_symbols(self):
        return [self.prop_type]


class CallbackSymbol(FunctionSymbol):
    """
    Banana banana
    """
    __tablename__ = 'callbacks'
    id_ = Column(Integer, ForeignKey('functions.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'callbacks',
    }

    def get_type_name(self):
        return "Callback"


class EnumSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'enums'
    id_ = Column(Integer, ForeignKey('symbols.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'enums',
    }
    members = Column(PickleType)
    raw_text = Column(String)
    anonymous = Column(Boolean)

    def __init__(self, **kwargs):
        self.members = {}
        self.raw_text = ''
        self.anonymous = False
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.members

    def get_extra_links(self):
        return [m.link for m in self.members]

    def get_type_name(self):
        return "Enumeration"


class StructSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'structs'
    id_ = Column(Integer, ForeignKey('symbols.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'structs',
    }
    members = Column(PickleType)
    raw_text = Column(String)
    anonymous = Column(Boolean)

    def __init__(self, **kwargs):
        self.members = {}
        self.anonymous = False
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.members

    def get_extra_links(self):
        return [m.link for m in self.members]

    def get_type_name(self):
        return "Structure"

# FIXME: and this is C-specific


class MacroSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'macros'
    id_ = Column(Integer, ForeignKey('symbols.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'macros',
    }
    original_text = Column(String)


class FunctionMacroSymbol(MacroSymbol):
    """
    Banana banana
    """
    __tablename__ = 'function_macros'
    id_ = Column(Integer, ForeignKey('macros.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'function_macros',
    }

    parameters = Column(MutableList.as_mutable(PickleType))
    return_value = Column(MutableList.as_mutable(PickleType))

    def __init__(self, **kwargs):
        self.parameters = []
        self.return_value = [None]
        MacroSymbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.parameters + self.return_value

    def get_type_name(self):
        return "Function macro"


class ConstantSymbol(MacroSymbol):
    """
    Banana banana
    """
    __tablename__ = 'constants'
    id_ = Column(Integer, ForeignKey('macros.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'constants',
    }

    def get_type_name(self):
        return "Constant"


class ExportedVariableSymbol(MacroSymbol):
    """
    Banana banana
    """
    __tablename__ = 'exported_variables'
    id_ = Column(Integer, ForeignKey('macros.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'exported_variables',
    }
    type_qs = Column(PickleType)

    def get_type_name(self):
        return "Exported variable"

    def get_children_symbols(self):
        return [self.type_qs]


class AliasSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'aliases'
    id_ = Column(Integer, ForeignKey('symbols.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'aliases',
    }
    aliased_type = Column(PickleType)

    def get_type_name(self):
        return "Alias"

    def get_children_symbols(self):
        return [self.aliased_type]


class ClassSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'classes'
    id_ = Column(Integer, ForeignKey('symbols.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'classes',
    }
    # FIXME: multiple inheritance
    hierarchy = Column(PickleType)
    children = Column(PickleType)

    def __init__(self, **kwargs):
        self.hierarchy = []
        self.children = {}
        Symbol.__init__(self, **kwargs)

    def get_type_name(self):
        return "Class"

    def get_children_symbols(self):
        return self.hierarchy + list(self.children.values())

class InterfaceSymbol(ClassSymbol):
    """
    Banana banana
    """
    __tablename__ = 'interfaces'
    id_ = Column(Integer, ForeignKey('classes.id_'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'interfaces',
    }
    prerequisites = Column(PickleType)

    def __init__(self, **kwargs):
        self.prerequisites = []
        ClassSymbol.__init__(self, **kwargs)

    def get_type_name(self):
        return "Interface"

    def get_children_symbols(self):
        return self.prerequisites + ClassSymbol.get_children_symbols(self)
