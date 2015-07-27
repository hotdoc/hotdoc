# -*- coding: utf-8 -*-

import os
import re
import json
import logging
import dagger

from datetime import datetime
from xml.sax.saxutils import unescape

from gnome_markdown_filter import GnomeMarkdownFilter
from pandoc_client import pandoc_converter
from pandocfilters import BulletList

import clang.cindex
from clang.cindex import *

import linecache
import uuid


def ast_node_is_function_pointer (ast_node):
    if ast_node.kind == clang.cindex.TypeKind.POINTER and \
            ast_node.get_pointee().get_result().kind != \
            clang.cindex.TypeKind.INVALID:
        return True
    return False


class SymbolResolver(object):
    def __init__(self, transformer):
        self.__transformer = transformer

    def resolve_type(self, ident):
        try:
            matches = self.__transformer.split_ctype_namespaces(ident)
        except ValueError:
            return None

        best_node = None
        for namespace, name in matches:
            node = namespace.get(name)
            if node:
                if best_node is None:
                    best_node = node
                elif node.doc and not best_node.doc:
                    best_node = node

        return best_node

    def __resolve_qualified_symbol (self, parent, symbol):
        split = symbol.split ('---')
        symbol = split[0]
        qualifier = split[1]
        if qualifier == 'Property':
            for prop in parent.properties:
                if prop.name == symbol:
                    return prop
        elif qualifier == 'VFunction':
            for meth in parent.virtual_methods:
                if meth.name == symbol:
                    return meth
        elif qualifier == 'Field':
            for field in parent.fields:
                if field.name == symbol:
                    return field
        elif qualifier == 'Signal':
            for signal in parent.signals:
                if signal.name == symbol:
                    return signal

        return None

    def resolve_symbol(self, symbol):
        split = None
        if "::" in symbol:
            split = symbol.split ('::')
            parent = self.resolve_type (split[0])
            return self.__resolve_qualified_symbol (parent, split[1])

        try:
            matches = self.__transformer.split_csymbol_namespaces(symbol)
        except ValueError:
            return None
        for namespace, name in matches:
            node = namespace.get_by_symbol(symbol)
            if node:
                return node

        if not node:
            for namespace, name in matches:
                node = namespace.get(name)
                if node:
                    return node
        return None


class Link (object):
    def get_link (self):
        raise NotImplementedError


class ExternalLink (Link):
    def __init__ (self, symbol, local_prefix, remote_prefix, filename, title):
        self.symbol = symbol
        self.local_prefix = local_prefix
        self.remote_prefix = remote_prefix
        self.filename = filename
        self.title = title

    def get_link (self):
        return "%s/%s" % (self.remote_prefix, self.filename)


class LocalLink (Link):
    def __init__(self, id_, pagename, title):
        self.id_ = id_
        self.pagename = pagename
        self.title = title

    def get_link (self):
        if (self.id_):
            return "%s#%s" % (self.pagename, self.id_)
        else:
            return self.pagename


class ExternalLinkResolver(object):
    def __init__(self):
        self.__all_links = {}
        self.__gather_gtk_doc_links ()

    def get_named_link (self, name):
        link = None
        try:
            link = self.__all_links[name]
        except KeyError:
            pass
        return link

    def __gather_gtk_doc_links (self):
        if not os.path.exists(os.path.join("/usr/share/gtk-doc/html")):
            print "no gtk doc to look at"
            return

        for node in os.listdir(os.path.join(DATADIR, "gtk-doc", "html")):
            dir_ = os.path.join(DATADIR, "gtk-doc/html", node)
            if os.path.isdir(dir_) and not "gst" in dir_:
                try:
                    self.__parse_sgml_index(dir_)
                except IOError:
                    pass

    def __parse_sgml_index(self, dir_):
        symbol_map = dict({})
        remote_prefix = ""
        with open(os.path.join(dir_, "index.sgml"), 'r') as f:
            for l in f:
                if l.startswith("<ONLINE"):
                    remote_prefix = l.split('"')[1]
                elif l.startswith("<ANCHOR"):
                    split_line = l.split('"')
                    filename = split_line[3].split('/', 1)[-1]
                    title = split_line[1].replace('-', '_')
                    link = ExternalLink (split_line[1], dir_, remote_prefix,
                            filename, title)
                    self.__all_links[title] = link


class SymbolFactory (object):
    def __init__(self, doc_formatter, extensions, comments):
        self.__comments = comments
        self.__doc_formatter = doc_formatter
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
        while (type_.kind == TypeKind.POINTER):
            self.__apply_qualifiers(type_, tokens)
            tokens.append ('*')
            type_ = type_.get_pointee()

        if type_.kind == TypeKind.TYPEDEF:
            d = type_.get_declaration ()
            link = self.__doc_formatter.get_named_link (d.displayname)
            if link:
                tokens.append (link)
            else:
                tokens.append (d.displayname + ' ')
        else:
            link = self.__doc_formatter.get_named_link (type_.spelling)
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
        self.formatted_doc = self.__doc_formatter.format_doc (self._comment)
        out, standalone = self.__doc_formatter._format_symbol (self)
        self.detailed_description = out
        if standalone:
            self.__doc_formatter.write_symbol (self)
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

    def get_named_link (self, ident, search_remote=True):
        return self.__doc_formatter.get_named_link (ident, search_remote)


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


class Annotation (object):
    def __init__(self, nick, help_text):
        self.nick = nick
        self.help_text = help_text


class Flag (object):
    def __init__ (self, nick, link):
        self.nick = nick
        self.link = link


class RunLastFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Run Last",
                "https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-RUN-LAST:CAPS")


class RunFirstFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Run First",
                "https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-RUN-FIRST:CAPS")


class RunCleanupFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Run Cleanup",
                "https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-RUN-CLEANUP:CAPS")


class WritableFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Write", None)


class ReadableFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Read", None)


class ConstructFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Construct", None)


class ConstructOnlyFlag (Flag):
    def __init__(self):
        Flag.__init__ (self, "Construct Only", None)


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


class ClassSymbol (SectionSymbol):
    pass


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

class Formatter(object):
    def __init__ (self, symbols, external_symbols, comments, include_directories, index_file, output,
            extensions, do_class_aggregation=False):
        self.__include_directories = include_directories
        self.__do_class_aggregation = do_class_aggregation
        self.__output = output
        self.__index_file = index_file
        self.__symbols = symbols
        self.__external_symbols = external_symbols
        self.__comments = comments

        self.__link_resolver = ExternalLinkResolver ()
        self.__symbol_factory = SymbolFactory (self, extensions, comments)
        self.__local_links = {}
        self.__gnome_markdown_filter = GnomeMarkdownFilter (os.path.dirname(index_file))
        self.__gnome_markdown_filter.set_formatter (self)

        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}

    def lookup_ast_node (self, name):
        return self.__symbols.get(name) or self.__external_symbols.get(name)

    def lookup_underlying_type (self, name):
        ast_node = self.lookup_ast_node (name)
        if not ast_node:
            return None

        while ast_node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            t = ast_node.underlying_typedef_type
            ast_node = t.get_declaration()
        return ast_node.kind

    def create_symbols(self):
        n = datetime.now()
        sf = SectionFilter (os.path.dirname(self.__index_file), self.__symbols,
                self.__comments, self, self.__symbol_factory)
        sf.create_symbols (os.path.basename(self.__index_file))
        self.__local_links = sf.local_links
        print "Markdown parsing done", datetime.now() - n
        return sf.sections

    def __format_section (self, section):
        out = ""
        section.do_format ()
        #with open (os.path.join (self.__output, filename), 'w') as f:
        #    if section.parsed_contents and not section.ast_node:
        #        out += pandoc_converter.convert("json", "html", json.dumps
        #                (section.parsed_contents))
            #out += self._format_class (section, True)
        #    section.filename = os.path.basename(filename)
            #f.write (out.encode('utf-8'))

        for section in section.sections:
            self.__format_section (section)

    def write_symbol (self, symbol):
        path = os.path.join (self.__output, symbol.link.pagename)
        with open (path, 'w') as f:
            f.write (symbol.detailed_description.encode('utf-8'))

    def format (self):
        n = datetime.now ()
        sections = self.create_symbols ()

        for section in sections:
            self.__format_section (section)

    def get_named_link(self, ident, search_remote=True):
        link = None
        try:
            link = self.__local_links [ident]
        except KeyError:
            if search_remote:
                link = self.__link_resolver.get_named_link (ident)
        return link

    def __format_doc_string (self, docstring):
        if not docstring:
            return ""

        out = ""
        docstring = unescape (docstring)
        json_doc = self.__gnome_markdown_filter.filter_text (docstring)
        html_text = pandoc_converter.convert ("json", "html", json.dumps (json_doc))
        return html_text

    def format_doc (self, comment):
        out = ""
        if comment:
            out += self.__format_doc_string (comment.description)
        return out

    def __warn_not_implemented (self, func):
        if func in self.__not_implemented_methods:
            return
        self.__not_implemented_methods [func] = True
        logging.warning ("%s not implemented !" % func) 

    # Virtual methods

    def _get_extension (self):
        """
        The extension to append to the filename
        ('markdown', 'html')
        """
        self.__warn_not_implemented (self._get_extension)
        return ""
