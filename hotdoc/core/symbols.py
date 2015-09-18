# -*- coding: utf-8 -*-

import re
import linecache
import uuid

# FIXME: This will have to be abstracted, might be involved :)
import clang.cindex

from .links import LocalLink, Link
from ..utils.simple_signals import Signal
from ..utils.utils import all_subclasses
from .doc_tool import doc_tool

def ast_node_is_function_pointer (ast_node):
    if ast_node.kind == clang.cindex.TypeKind.POINTER and \
            ast_node.get_pointee().get_result().kind != \
            clang.cindex.TypeKind.INVALID:
        return True
    return False

class Symbol (object):
    def __init__(self, symbol, comment):
        self._symbol = symbol
        self.comment = comment
        self.original_text = None
        self.detailed_description = None
        self.link = LocalLink (self._make_unique_id(), "", self._make_name())

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
        self.tags = self.parse_tags ()
        return doc_tool.formatter.format_symbol (self)

    def _make_name (self):
        if type(self._symbol) in [clang.cindex.Cursor, clang.cindex.Type]:
            return self._symbol.spelling
        elif type(self._symbol) in [str, unicode]:
            return self._symbol
        print "Warning, you need to provide a name creation routine for", type (self), type(self._symbol)
        raise NotImplementedError

    def _make_unique_id (self):
        if type(self._symbol) == clang.cindex.Cursor:
            return self._symbol.spelling
        elif type (self._symbol) == str:
            return self._symbol
        res = uuid.uuid4()
        return str(res)

    def get_extra_links (self):
        return []

    def add_annotation (self, annotation):
        self.annotations.append (annotation)


    def get_type_name (self):
        return ''

class Tag:
    def __init__(self, name, value):
        self.name = name
        self.description = value


class FunctionSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.return_value = None
        self.is_method = False

    def do_format (self):
        return_comment = self.comment.tags.get('returns')
        if return_comment:
            self.comment.tags.pop('returns', None)

        if not self.return_value:
            self.return_value = \
                    doc_tool.symbol_factory.make_return_value_symbol(self._symbol.result_type,
                            return_comment)

        self.parameters = []
        for param in self._symbol.get_arguments():
            param_comment = self.comment.params.get (param.displayname)
            parameter = doc_tool.symbol_factory.make_parameter_symbol \
                    (param.type, param_comment, param.displayname)
            self.parameters.append (parameter)

        return Symbol.do_format (self)


    def get_type_name (self):
        if self.is_method:
            return 'Method'
        return 'Function'

class CallbackSymbol (FunctionSymbol):
    def do_format (self):
        self.parameters = []
        for child in self._symbol.get_children():
            if not self.return_value:
                self.return_value = \
                doc_tool.symbol_factory.make_return_value_symbol (child.type,
                        self.comment.tags.get("returns"))
            else:
                param_comment = self.comment.params.get (child.spelling)
                parameter = doc_tool.symbol_factory.make_parameter_symbol \
                        (child.type, param_comment, child.displayname)
                self.parameters.append (parameter)

        self.comment.tags.pop('returns', None)
        return Symbol.do_format (self)

    def get_type_name (self):
        return "Callback"

class EnumSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.members = []
        underlying = self._symbol.underlying_typedef_type
        decl = underlying.get_declaration()
        for member in decl.get_children():
            member_comment = self.comment.params.get (member.spelling)
            member_value = member.enum_value
            member = doc_tool.symbol_factory.make_simple_symbol (member,
                    member_comment)
            member.enum_value = member_value
            doc_tool.link_resolver.add_local_link (member.link)
            self.members.append (member)

    def get_extra_links (self):
        return [m.link for m in self.members]

    def do_format (self):
        for member in self.members:
            member.do_format ()
        return Symbol.do_format (self)

    def get_type_name (self):
        return "Enumeration"

class StructSymbol (Symbol):
    public_pattern = re.compile('\s*/\*\<\s*public\s*\>\*/.*')
    private_pattern = re.compile('\s*/\*\<\s*private\s*\>\*/.*')
    protected_pattern = re.compile('\s*/\*\<\s*protected\s*\>\*/.*')

    def do_format (self):
        underlying = self._symbol.underlying_typedef_type
        decl = underlying.get_declaration()
        self.raw_text, public_fields = self.__parse_public_fields (decl)
        self.members = []
        for field in public_fields:
            member_comment = self.comment.params.get (field.spelling)
            
            member = doc_tool.symbol_factory.make_field_symbol (
                    field.type, member_comment, field.spelling)
            member.do_format()
            self.members.append (member)
        return Symbol.do_format (self)

    # Quite a hairy method, but the lack of constraints on the public /
    # private delimiters make it so.
    def __parse_public_fields (self, decl):
        tokens = decl.translation_unit.get_tokens(extent=decl.extent)
        delimiters = []

        filename = str(decl.location.file)

        start = decl.extent.start.line
        end = decl.extent.end.line + 1
        original_lines = [linecache.getline(filename, i).rstrip() for i in range(start,
            end)]

        public = True
        if (self.__locate_delimiters(tokens, delimiters)):
            public = False

        children = []
        for child in decl.get_children():
            children.append(child)

        delimiters.reverse()
        if not delimiters:
            return '\n'.join (original_lines), children

        public_children = []
        children = []
        for child in decl.get_children():
            children.append(child)
        children.reverse()
        if children:
            next_child = children.pop()
        else:
            next_child = None
        next_delimiter = delimiters.pop()

        final_text = []

        found_first_child = False

        for i, line in enumerate(original_lines):
            lineno = i + start
            if next_delimiter and lineno == next_delimiter[1]:
                public = next_delimiter[0]
                if delimiters:
                    next_delimiter = delimiters.pop()
                else:
                    next_delimiter = None
                continue

            if not next_child or lineno < next_child.location.line:
                if public or not found_first_child:
                    final_text.append (line)
                continue

            if lineno == next_child.location.line:
                found_first_child = True
                if public:
                    final_text.append (line)
                    public_children.append (next_child)
                while next_child.location.line == lineno:
                    if not children:
                        public = True
                        next_child = None
                        break
                    next_child = children.pop()

        return ('\n'.join(final_text), public_children)

    def __locate_delimiters (self, tokens, delimiters):
        had_public = False
        for tok in tokens:
            if tok.kind == clang.cindex.TokenKind.COMMENT:
                if self.public_pattern.match (tok.spelling):
                    had_public = True
                    delimiters.append((True, tok.location.line))
                elif self.private_pattern.match (tok.spelling):
                    delimiters.append((False, tok.location.line))
                elif self.protected_pattern.match (tok.spelling):
                    delimiters.append((False, tok.location.line))
        return had_public

    def _make_unique_id (self):
        return self._symbol.spelling + "-struct"

    def get_type_name (self):
        return "Structure"

class MacroSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)

        start = self._symbol.extent.start.line
        end = self._symbol.extent.end.line + 1
        filename = str(self._symbol.location.file)
        original_lines = [linecache.getline(filename, i).rstrip() for i in range(start,
            end)]
        self.original_text = '\n'.join(original_lines)

class FunctionMacroSymbol (MacroSymbol):
    def __init__(self, *args):
        MacroSymbol.__init__(self, *args)
        self.return_value = None
        self.parameters = []

    def do_format (self):
        return_comment = self.comment.tags.get ('returns')
        if return_comment:
            self.comment.tags.pop ('returns')
            self.return_value = \
                doc_tool.symbol_factory.make_untyped_return_value_symbol (return_comment)

        for param_name, comment in self.comment.params.iteritems():
            parameter = doc_tool.symbol_factory.make_custom_parameter_symbol(comment, [], param_name)
            self.parameters.append (parameter)
        return Symbol.do_format(self)

    def get_type_name (self):
        return "Function macro"

class ConstantSymbol (MacroSymbol):
    def get_type_name (self):
        return "Constant"


class ExportedVariableSymbol (MacroSymbol):
    def get_type_name (self):
        return "Exported variable"


class QualifiedSymbol (Symbol):
    def __init__(self, tokens, *args):
        self.type_tokens = tokens
        Symbol.__init__(self, *args)

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
    def do_format (self):
        self.aliased_type = doc_tool.symbol_factory.make_qualified_symbol (
                self._symbol.underlying_typedef_type, None)
        return Symbol.do_format (self)

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

    def __apply_qualifiers (self, type_, tokens):
        if type_.is_const_qualified():
            tokens.append ('const ')
        if type_.is_restrict_qualified():
            tokens.append ('restrict ')
        if type_.is_volatile_qualified():
            tokens.append ('volatile ')

    def __make_c_style_type_name (self, type_):
        tokens = []
        while (type_.kind == clang.cindex.TypeKind.POINTER):
            self.__apply_qualifiers(type_, tokens)
            tokens.append ('*')
            type_ = type_.get_pointee()

        if type_.kind == clang.cindex.TypeKind.TYPEDEF:
            d = type_.get_declaration ()
            link = doc_tool.link_resolver.get_named_link (d.displayname)
            if link:
                tokens.append (link)
            else:
                tokens.append (d.displayname + ' ')
            self.__apply_qualifiers(type_, tokens)
        else:
            link = doc_tool.link_resolver.get_named_link (type_.spelling)
            if link:
                tokens.append (link)
            else:
                tokens.append (type_.spelling + ' ')

        tokens.reverse()
        return tokens

    def __signal_new_symbol (self, symbol):
        res = self.new_symbol_signals[type(symbol)](symbol)
        if False in res:
            return None
        res = self.new_symbol_signals[Symbol](symbol)
        if False in res:
            return None

        doc_tool.link_resolver.add_local_link (symbol.link)
        return symbol

    def make_parameter_symbol (self, type_, comment, argname):
        tokens = self.__make_c_style_type_name (type_)
        do_it = False
        for t in tokens:
            if not isinstance (t, Link) and "char" in t:
                do_it = True
        return self.__signal_new_symbol(ParameterSymbol (argname, tokens, type_, comment))

    def make_qualified_symbol (self, type_, comment, tokens=None):
        if tokens is None:
            tokens = self.__make_c_style_type_name (type_)
        return self.__signal_new_symbol(QualifiedSymbol (tokens, type_, comment))

    def make_field_symbol (self, ast_node, comment, member_name):
        is_function_pointer = ast_node_is_function_pointer (ast_node)
        tokens = self.__make_c_style_type_name (ast_node)

        return self.__signal_new_symbol(FieldSymbol (is_function_pointer,
            member_name, tokens, ast_node, comment))

    def make_simple_symbol (self, symbol, comment):
        return self.__signal_new_symbol(Symbol (symbol, comment))

    def make_return_value_symbol (self, type_, comment):
        tokens = self.__make_c_style_type_name (type_)
        return self.__signal_new_symbol(ReturnValueSymbol (tokens, type_,
            comment))

    def make_custom_return_value_symbol (self, comment, type_tokens):
        return self.__signal_new_symbol(ReturnValueSymbol (type_tokens, '', comment))

    def make_custom_parameter_symbol (self, comment, type_tokens, argname):
        return self.__signal_new_symbol(ParameterSymbol (argname, type_tokens, argname, comment))

    def make_untyped_return_value_symbol (self, comment):
        return self.__signal_new_symbol (ReturnValueSymbol ([],
            "", comment))

    def make (self, symbol, comment):
        klass = None

        if symbol.spelling in doc_tool.c_source_scanner.new_symbols:
            sym = doc_tool.c_source_scanner.new_symbols[symbol.spelling]
            return self.__signal_new_symbol (sym)

        return None

    def make_custom (self, symbol, comment, klass):
        return self.__signal_new_symbol(klass (symbol, comment))

    def make_section(self, symbol, comment):
        res = None
        for extension in doc_tool.extensions:
            klass, extra_args = extension.get_section_type (symbol)
            if klass:
                res = klass (extra_args, symbol, comment)

        if not res:
            res = SectionSymbol (symbol, comment)

        doc_tool.link_resolver.add_local_link (res.link)
        return self.__signal_new_symbol(res)


from sections import SectionSymbol

class ClassSymbol (SectionSymbol):
    def __init__(self, *args):
        self.hierarchy = []
        self.children = []
        SectionSymbol.__init__(self, *args)

    def get_type_name (self):
        return "Class"
