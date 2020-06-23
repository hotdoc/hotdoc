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

from hotdoc.core.comment import comment_from_tag
from hotdoc.core.links import Link


# pylint: disable=too-many-instance-attributes
class Symbol:
    """
    The base class for all symbols, there should be no reason for
    instantiating it directly.
    """
    __tablename__ = 'symbols'

    def __init__(self):
        self.extension_contents = {}
        self.extension_attributes = {}
        self.skip = False

        self.extra = {}
        self.comment = None
        self.unique_name = None
        self.display_name = None
        self.filename = None
        self.lineno = -1
        self.extent_start = -1
        self.extent_end = -1
        self.link = None
        self.project_name = None
        self.parent_name = None
        self.aliases = []

    def __repr__(self):
        return "%s(unique_name=%s, filename=%s, project=%s)" % (
            type(self).__name__, self.unique_name, self.filename,
            self.project_name)

    @classmethod
    def get_plural_name(cls):
        """Default implementation of the vmethod
        to retrieve Plurial form of the symbol name."""
        return cls.__tablename__.replace("_", " ").title()

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
        return self.aliases

    # pylint: disable=unidiomatic-typecheck
    # pylint: disable=no-member
    def update_children_comments(self):
        """
        Banana banana
        """
        if self.comment is None:
            return

        for sym in self.get_children_symbols():
            if isinstance(sym, ParameterSymbol):
                sym.comment = self.comment.params.get(sym.argname)
            elif isinstance(sym, FieldSymbol):
                if not sym.comment or not sym.comment.description:
                    sym.comment = self.comment.params.get(sym.member_name)
            elif isinstance(sym, EnumMemberSymbol):
                if not sym.comment or not sym.comment.description:
                    sym.comment = self.comment.params.get(sym.unique_name)
            elif isinstance(sym, ReturnItemSymbol):
                tag = self.comment.tags.get('returns')
                sym.comment = comment_from_tag(tag)
            elif type(sym) == Symbol:
                sym.comment = self.comment.params.get(sym.display_name)

            if isinstance(sym, Symbol):
                sym.update_children_comments()

    def make_name(self):
        return self.display_name or self.unique_name

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
            self.link = Link(self.unique_name, self.make_name(),
                             self.unique_name)

        self.link = link_resolver.upsert_link(self.link, overwrite_ref=True)

        for sym in self.get_children_symbols():
            if sym:
                sym.resolve_links(link_resolver)


class QualifiedSymbol:
    """
    Banana banana
    """

    def __init__(self, type_tokens=None):
        self.input_tokens = type_tokens or []
        self.comment = None
        self.extension_attributes = {}
        self.extension_contents = {}

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

        for child in self.get_children_symbols():
            child.resolve_links(link_resolver)

        for tok in self.input_tokens:
            if isinstance(tok, Link):
                self.type_link = link_resolver.upsert_link(tok)
                self.type_tokens.append(self.type_link)
            else:
                self.type_tokens.append(tok)


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

    def __init__(self, **kwargs):
        self.is_function_pointer = False
        self.qtype = None
        self.member_name = None
        Symbol.__init__(self, **kwargs)

    def make_name(self):
        return self.member_name

    def get_children_symbols(self):
        return [self.qtype] + super().get_children_symbols()

    # pylint: disable=no-self-use
    def get_type_name(self):
        """
        Banana banana
        """
        return "Attribute"


class EnumMemberSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'members'


class FunctionSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'functions'

    def __init__(self, **kwargs):
        self.parameters = []
        self.return_value = [None]
        self.throws = False
        self.is_ctor_for = None
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.parameters + self.return_value + super().get_children_symbols()

    def get_type_name(self):
        return 'Function'


class MethodSymbol(FunctionSymbol):
    """Banana Banana"""
    __tablename__ = 'methods'

    def get_type_name(self):
        return "Method"


class ClassMethodSymbol(FunctionSymbol):
    """Banana Banana"""
    __tablename__ = 'class_methods'

    def get_type_name(self):
        return "Class method"


class ConstructorSymbol(FunctionSymbol):
    """Banana Banana"""
    __tablename__ = 'constructors'

    def get_type_name(self):
        return "Constructor"


class SignalSymbol(FunctionSymbol):
    """
    Banana banana
    """
    __tablename__ = 'signals'

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
    __tablename__ = 'virtual_methods'

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

    def __init__(self, **kwargs):
        self.prop_type = None
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return [self.prop_type] + super().get_children_symbols()


class CallbackSymbol(FunctionSymbol):
    """
    Banana banana
    """
    __tablename__ = 'callbacks'

    def get_type_name(self):
        return "Callback"


class EnumSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'enumerations'

    def __init__(self, **kwargs):
        self.members = {}
        self.raw_text = ''
        self.anonymous = False
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.members + super().get_children_symbols()

    def get_extra_links(self):
        return [m.link for m in self.members]

    def get_type_name(self):
        return "Enumeration"


class StructSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'structures'

    def __init__(self, **kwargs):
        self.members = {}
        self.anonymous = False
        self.members = []
        self.raw_text = None
        Symbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.members + super().get_children_symbols()

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

    def __init__(self, **kwargs):
        self.original_text = None
        Symbol.__init__(self, **kwargs)


class FunctionMacroSymbol(MacroSymbol):
    """
    Banana banana
    """
    __tablename__ = 'function_macros'

    def __init__(self, **kwargs):
        self.parameters = []
        self.return_value = [None]
        MacroSymbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return self.parameters + self.return_value + super().get_children_symbols()

    def get_type_name(self):
        return "Function macro"


class ConstantSymbol(MacroSymbol):
    """
    Banana banana
    """
    __tablename__ = 'constants'

    def get_type_name(self):
        return "Constant"


class ExportedVariableSymbol(MacroSymbol):
    """
    Banana banana
    """
    __tablename__ = 'exported_variables'

    def __init__(self, **kwargs):
        self.type_qs = None
        MacroSymbol.__init__(self, **kwargs)

    def get_type_name(self):
        return "Exported variable"

    def get_children_symbols(self):
        return [self.type_qs] + super().get_children_symbols()


class AliasSymbol(Symbol):
    """
    Banana banana
    """
    __tablename__ = 'aliases'

    def __init__(self, **kwargs):
        self.aliased_type = None
        Symbol.__init__(self, **kwargs)

    def get_type_name(self):
        return "Alias"

    def get_children_symbols(self):
        return [self.aliased_type] + super().get_children_symbols()


class ClassSymbol(StructSymbol):
    """
    Banana banana
    """
    __tablename__ = 'classes'

    def __init__(self, **kwargs):
        self.hierarchy = []
        self.children = {}
        StructSymbol.__init__(self, **kwargs)

    def get_type_name(self):
        return "Class"

    def get_children_symbols(self):
        return self.hierarchy + list(
            self.children.values()) + super().get_children_symbols()


class InterfaceSymbol(ClassSymbol):
    """
    Banana banana
    """
    __tablename__ = 'interfaces'

    def __init__(self, **kwargs):
        self.prerequisites = []
        ClassSymbol.__init__(self, **kwargs)

    def get_type_name(self):
        return "Interface"

    def get_children_symbols(self):
        return self.prerequisites + super().get_children_symbols()


class ProxySymbol(Symbol):
    """A proxy type to handle aliased symbols"""
    __tablename__ = 'proxy_symbols'

    def __init__(self, **kwargs):
        self.target = None
        Symbol.__init__(self, **kwargs)
