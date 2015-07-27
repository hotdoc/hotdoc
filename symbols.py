# -*- coding: utf-8 -*-

import re
import linecache
import uuid

import clang.cindex

from links import link_resolver, LocalLink
from clangizer import ast_node_is_function_pointer

class Symbol (object):
    def __init__(self, symbol, comment, doc_formatter, symbol_factory=None):
        self.__doc_formatter = doc_formatter
        self._symbol_factory = symbol_factory
        self._symbol = symbol
        self._comment = comment
        self.original_text = None
        self.annotations = []
        self.flags = []
        self.link = LocalLink (self._make_unique_id(), "", self._make_name())
        self.detailed_description = None

    def do_format (self):
        self.__doc_formatter.format_symbol (self)
        return True

    def _lookup_ast_node (self, name):
        return self.__doc_formatter.lookup_ast_node (name)

    def _lookup_underlying_type (self, name):
        return self.__doc_formatter.lookup_underlying_type(name)

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
        return str(hex(uuid.getnode()))

    def get_extra_links (self):
        return []

    def add_annotation (self, annotation):
        self.annotations.append (annotation)


class FunctionSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)

    def do_format (self):
        self.return_value = \
                self._symbol_factory.make_return_value_symbol(self._symbol.result_type,
                        self._comment.tags.get("returns"))

        self.return_value.do_format()
        self.parameters = []
        for param in self._symbol.get_arguments():
            param_comment = self._comment.params.get (param.displayname)
            parameter = self._symbol_factory.make_parameter_symbol \
                    (param.type, param_comment, param.displayname)
            parameter.do_format()
            self.parameters.append (parameter)

        return Symbol.do_format (self)


class CallbackSymbol (FunctionSymbol):
    def do_format (self):
        self.return_value = None
        self.parameters = []
        for child in self._symbol.get_children():
            if not self.return_value:
                self.return_value = \
                self._symbol_factory.make_return_value_symbol (child.type,
                        self._comment.tags.get("returns"))
                self.return_value.do_format()
            else:
                param_comment = self._comment.params.get (child.spelling)
                parameter = self._symbol_factory.make_parameter_symbol \
                        (child.type, param_comment, child.displayname)
                parameter.do_format()
                self.parameters.append (parameter)

        return Symbol.do_format (self)


class EnumSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.members = []
        underlying = self._symbol.underlying_typedef_type
        decl = underlying.get_declaration()
        for member in decl.get_children():
            member_comment = self._comment.params.get (member.spelling)
            member = self._symbol_factory.make_simple_symbol (member,
                    member_comment)
            link_resolver.add_local_link (member.link)
            self.members.append (member)

    def get_extra_links (self):
        return [m.link for m in self.members]

    def do_format (self):
        for member in self.members:
            member.do_format ()
        return Symbol.do_format (self)


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
            member_comment = self._comment.params.get (field.spelling)
            
            member = self._symbol_factory.make_field_symbol (
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
        original_lines = [linecache.getline(filename, i).strip() for i in range(start,
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


class MacroSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.original_text = linecache.getline (str(self._symbol.location.file),
                self._symbol.location.line).strip()


class FunctionMacroSymbol (MacroSymbol):
    def __init__(self, *args):
        MacroSymbol.__init__(self, *args)
        self.parameters = []

    def do_format (self):
        for param_name, comment in self._comment.params.iteritems():
            parameter = self._symbol_factory.make_custom_parameter_symbol(comment, [], param_name)
            parameter.do_format ()
            self.parameters.append (parameter)
        return Symbol.do_format(self)


class ConstantSymbol (MacroSymbol):
    pass


class QualifiedSymbol (Symbol):
    def __init__(self, tokens, *args):
        self.type_tokens = tokens
        Symbol.__init__(self, *args)


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


class AliasSymbol (Symbol):
    def do_format (self):
        self.aliased_type = self._symbol_factory.make_qualified_symbol (
                self._symbol.underlying_typedef_type, None)
        return Symbol.do_format (self)


class SymbolFactory (object):
    def __init__(self, doc_formatter, extensions, comments, source_scanner):
        self.__comments = comments
        self.__doc_formatter = doc_formatter
        self.source_scanner = source_scanner
        self.__extensions = extensions
        self.__symbol_classes = {
                    clang.cindex.CursorKind.FUNCTION_DECL: FunctionSymbol,
                }

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
            link = link_resolver.get_named_link (d.displayname)
            if link:
                tokens.append (link)
            else:
                tokens.append (d.displayname + ' ')
        else:
            link = link_resolver.get_named_link (type_.spelling)
            if link:
                tokens.append (link)
            else:
                tokens.append (type_.spelling + ' ')

        self.__apply_qualifiers(type_, tokens)

        tokens.reverse()
        return tokens

    def make_parameter_symbol (self, type_, comment, argname):
        tokens = self.__make_c_style_type_name (type_)
        return ParameterSymbol (argname, tokens, type_, comment,
                self.__doc_formatter, self)

    def make_qualified_symbol (self, type_, comment, tokens=None):
        if tokens is None:
            tokens = self.__make_c_style_type_name (type_)
        return QualifiedSymbol (tokens, type_, comment,
                self.__doc_formatter, self)

    def make_field_symbol (self, ast_node, comment, member_name):
        is_function_pointer = ast_node_is_function_pointer (ast_node)
        tokens = self.__make_c_style_type_name (ast_node)

        return FieldSymbol (is_function_pointer, member_name, tokens, ast_node, comment,
                self.__doc_formatter, self)

    def make_simple_symbol (self, symbol, comment):
        res = Symbol (symbol, comment, self.__doc_formatter,
                self)
        return res

    def make_return_value_symbol (self, type_, comment):
        tokens = self.__make_c_style_type_name (type_)
        return ReturnValueSymbol (tokens, type_, comment, self.__doc_formatter,
                    self)

    def make_custom_parameter_symbol (self, comment, type_tokens, argname):
        symbol = ParameterSymbol (argname, type_tokens, argname, comment,
                self.__doc_formatter, self)
        return symbol

    def make (self, symbol, comment):
        klass = None

        if symbol.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
            l = linecache.getline (str(symbol.location.file), symbol.location.line)
            # FIXME: hack, seems there's no better way to figure out if a macro is
            # function-like
            split = l.split()
            if '(' in split[1]:
                klass = FunctionMacroSymbol 
            else:
                klass = ConstantSymbol
        elif symbol.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            klass = FunctionSymbol
        elif symbol.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            t = symbol.underlying_typedef_type
            if ast_node_is_function_pointer (t):
                klass = CallbackSymbol
            else:
                d = t.get_declaration()
                if d.kind == clang.cindex.CursorKind.STRUCT_DECL:
                    klass = StructSymbol
                elif d.kind == clang.cindex.CursorKind.ENUM_DECL:
                    klass = EnumSymbol
                else:
                    klass = AliasSymbol

        res = None
        if klass:
            res = klass (symbol, comment, self.__doc_formatter, self)

        link_resolver.add_local_link (res.link)
        return res

    def make_custom (self, symbol, comment, klass):
        return klass (symbol, comment, self.__doc_formatter, self)

    def make_section(self, symbol, comment):
        res = None
        for extension in self.__extensions:
            klass, extra_args = extension.get_section_type (symbol)
            if klass:
                res = klass (symbol, comment, self.__doc_formatter, self)
                res.symbol_init (self.__comments, extra_args)

        if not res:
            res = SectionSymbol (symbol, comment, self.__doc_formatter, self)

        return res


from sections import SectionSymbol

class ClassSymbol (SectionSymbol):
    pass
