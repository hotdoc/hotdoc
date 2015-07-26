# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import logging
import dagger

from datetime import datetime
from lxml import etree
from giscanner import ast
from xml.sax.saxutils import unescape

from gnome_markdown_filter import GnomeMarkdownFilter
from pandoc_client import pandoc_converter
from pandocfilters import BulletList

import clang.cindex
from clang.cindex import *

import linecache

from giscanner.sourcescanner import CSYMBOL_TYPE_FUNCTION
from giscanner.sourcescanner import CTYPE_INVALID, CTYPE_VOID,\
CTYPE_BASIC_TYPE, CTYPE_TYPEDEF, CTYPE_STRUCT, CTYPE_UNION, CTYPE_ENUM,\
CTYPE_POINTER, CTYPE_ARRAY, CTYPE_FUNCTION

class NameFormatter(object):
    def __init__(self, language='python'):
        if language == 'C':
            self.__make_node_name = self.__make_c_node_name
        elif language == 'python':
            self.__make_node_name = self.__make_python_node_name

    def get_full_node_name(self, node):
        return self.__make_node_name (node)

    def __make_python_node_name (self, node):
        out = ""
        if type (node) in (ast.Namespace, ast.DocSection):
            return node.name

        if type (node) in (ast.Signal, ast.Property, ast.Field):
            qualifier = str (type (node)).split ('.')[-1].split ("'")[0]
            out = "%s.%s::%s---%s" % (node.namespace.name, node.parent.name,
                    qualifier)


        if type (node) == ast.VFunction:
            out = "%s.%s.do_%s" % (node.namespace.name, node.parent.name,
                    node.name)

        if type (node) in (ast.Function, ast.Class, ast.Enum, ast.Alias,
                ast.Record, ast.Bitfield, ast.Callback,
                ast.Constant, ast.Interface):
            while node:
                if out:
                    out = "%s.%s" % (node.name, out)
                else:
                    out = node.name

                if hasattr (node, "parent"):
                    node = node.parent
                else:
                    node = None

        return out

    def __make_c_node_name (self, node):
        out = ""
        if type (node) in (ast.Namespace, ast.DocSection):
            out = node.name

        elif type (node) in (ast.Signal, ast.Property, ast.Field, ast.VFunction):
            qualifier = str (type (node)).split ('.')[-1].split ("'")[0]
            out = "%s%s::%s---%s" % (node.namespace.name, node.parent.name,
                    node.name, qualifier)

        elif type (node) == ast.Function:
            while node:
                if out:
                    c_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                        node.name).lower()
                    c_name = re.sub('__', r'_', c_name)
                    out = "%s_%s" % (c_name, out)
                else:
                    out = node.name

                if hasattr (node, "parent"):
                    node = node.parent
                else:
                    node = None

        elif type (node) == ast.FunctionMacro:
            out = node.symbol

        elif type (node) in (ast.Class, ast.Enum, ast.Alias, ast.Record,
                ast.Callback, ast.Constant, ast.Bitfield, ast.Interface):
            if node.namespace:
                out = "%s%s" % (node.namespace.name, node.name)
            else:
                out = node.name

        return out

    def make_page_name (self, node):
        return self.__make_c_node_name (node)


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
    def __init__(self, symbol, pagename, title):
        self.__symbol = symbol
        self.pagename = pagename
        self.title = title

    def get_link (self):
        if (self.__symbol):
            return "%s#%s" % (self.pagename, self.__symbol)
        else:
            return self.pagename


class LinkResolver(object):
    def __init__(self):
        self.__name_formatter = NameFormatter ()
        self.__all_links = {}
        self.__gtk_doc_links = self.__gather_gtk_doc_links ()

    def __gather_gtk_doc_links (self):
        links = dict ({})

        if not os.path.exists(os.path.join("/usr/share/gtk-doc/html")):
            print "no gtk doc to look at"
            return

        for node in os.listdir(os.path.join(DATADIR, "gtk-doc", "html")):
            dir_ = os.path.join(DATADIR, "gtk-doc/html", node)
            if os.path.isdir(dir_) and not "gst" in dir_:
                try:
                    links[node] = self.__parse_sgml_index(dir_)
                except IOError:
                    pass

        return links

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

    def get_named_link (self, name):
        link = None
        try:
            link = self.__all_links[name]
        except KeyError:
            pass
        return link

def cname(base_type):
    return {
        CTYPE_INVALID: 'invalid',
        CTYPE_VOID: 'void',
        CTYPE_BASIC_TYPE: '%s ' % base_type.name,
        CTYPE_TYPEDEF: '%s ' % base_type.name,
        CTYPE_STRUCT: 'struct',
        CTYPE_UNION: 'union',
        CTYPE_ENUM: 'enum',
        CTYPE_POINTER: '*',
        CTYPE_ARRAY: '*',
        CTYPE_FUNCTION: 'function'}.get(base_type.type)

def cname_from_base_type(base_type):
    if not base_type:
        return ""
    res = cname (base_type)
    if base_type.base_type:
        return cname_from_base_type (base_type.base_type) + res
    return res

class SymbolFactory (object):
    def __init__(self, doc_formatter):
        self.__doc_formatter = doc_formatter
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

    def make_qualified_symbol (self, type_, comment, argname=None):
        tokens = self.__make_c_style_type_name (type_)
        if argname:
            res = ParameterSymbol (argname, tokens, type_, comment,
                    self.__doc_formatter, self)
        else:
            res = ReturnValueSymbol (tokens, type_, comment, self.__doc_formatter,
                    self)

        return res

    def make_untyped_parameter_symbol (self, comment, argname):
        symbol = ParameterSymbol (argname, None, None, comment,
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
            try:
                klass = self.__symbol_classes[symbol.kind]
            except KeyError:
                pass

        res = None
        if klass:
            res = klass (symbol, comment, self.__doc_formatter, self)
        return res


class Symbol (object):
    def __init__(self, symbol, comment, doc_formatter, symbol_factory=None):
        self.__doc_formatter = doc_formatter
        self._symbol_factory = symbol_factory
        self._symbol = symbol
        self._comment = comment
        self.type_name = ""
        self.original_text = None
        #if symbol:
        #    self.type_name = symbol.ident
        self.annotations = []
        self.flags = []
        self.filename = None
        self.link = None
        self.detailed_description = None

    def do_format (self):
        self.formatted_doc = self.__doc_formatter.format_doc (self._comment)
        out, standalone = self.__doc_formatter._format_symbol (self)
        self.detailed_description = out
        if standalone:
            self.__doc_formatter.write_symbol (self)
        return True

    def set_link (self, link):
        self.link = link

    def get_extra_links (self):
        return []

    def add_annotation (self, annotation):
        self.annotations.append (annotation)

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

class Section (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.symbols = []

    def add_symbol (self, symbol):
        self.symbols.append (symbol)


class EnumSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.members = []
        for member in self.ast_node.members:
            member_ = self._symbol_factory.make_simple_symbol (member,
                    member.symbol)
            self.members.append (member_)

    def get_extra_links (self):
        return ['%s' % member.type_name for member in self.members]

    def do_format (self):
        for member in self.members:
            member.do_format ()
        return Symbol.do_format(self)


class TypedSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.type_name = self.ast_node.name

    def do_format (self):
        if self.ast_node.type is None:
            return False

        if hasattr (self.ast_node, "private") and self.ast_node.private: #Fields
            return False

        self.type_ = self._symbol_factory.make_qualified_symbol (self.ast_node)
        return Symbol.do_format (self)

class PropertySymbol (TypedSymbol):
    def __init__(self, *args):
        TypedSymbol.__init__(self, *args)
        if self.ast_node.readable:
            self.flags.append (ReadableFlag ())
        if self.ast_node.writable:
            self.flags.append (WritableFlag ())
        if self.ast_node.construct_only:
            self.flags.append (ConstructOnlyFlag ())
        elif self.ast_node.construct:
            self.flags.append (ConstructFlag ())


class FieldSymbol (TypedSymbol):
    pass


class AliasSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)

    def do_format (self):
        if self.ast_node.target is None:
            return False

        self.type_ = self._symbol_factory.make_qualified_symbol (self.ast_node)
        return Symbol.do_format (self)


class ConstantSymbol (Symbol):
    def do_format (self):
        self.value = self.ast_node.value
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
                self._symbol_factory.make_qualified_symbol(self._symbol.result_type,
                        self._comment.tags.get("returns"))

        self.return_value.do_format()
        self.parameters = []
        for param in self._symbol.get_arguments():
            param_comment = self._comment.params.get (param.displayname)
            parameter = self._symbol_factory.make_qualified_symbol \
                    (param.type, param_comment, param.displayname)
            parameter.do_format()
            self.parameters.append (parameter)

        return Symbol.do_format (self)


class CallbackSymbol (FunctionSymbol):
    pass


class VirtualFunctionSymbol (FunctionSymbol):
    def __init__(self, *args):
        FunctionSymbol.__init__(self, *args)
        self.type_name = self.ast_node.name


class SignalSymbol (VirtualFunctionSymbol):
    #FIXME ...
    def __add_missing_signal_parameters (self, node):
        if node.instance_parameter:
            return

        node.instance_parameter = ast.Parameter ("self",
                node.parent.create_type())
        node.instance_parameter.doc = "the object which received the signal."
        user_data_param = ast.Parameter ("user_data", ast.Type
                (target_fundamental = "gpointer", ctype="gpointer"))
        user_data_param.doc = "user data set when the signal handler was connected."
        node.parameters.append (user_data_param)

    def do_format (self):
        self.__add_missing_signal_parameters (self.ast_node)
        if self.ast_node.when == "last":
            self.flags.append (RunLastFlag ())
        elif self.ast_node.when == "first":
            self.flags.append (RunFirstFlag ())
        elif self.ast_node.when == "cleanup":
            self.flags.append (RunCleanupFlag ())

        return FunctionSymbol.do_format (self)


class FunctionMacroSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.original_text = linecache.getline (str(self._symbol.location.file),
                self._symbol.location.line).strip()
        self.parameters = []

    def do_format (self):
        for param_name, comment in self._comment.params.iteritems():
            parameter = self._symbol_factory.make_untyped_parameter_symbol (comment, param_name)
            parameter.do_format ()
            self.parameters.append (parameter)
        return Symbol.do_format(self)


class RecordSymbol (Symbol):
    pass


class Dependency (object):
    def __init__(self, filename):
        self.filename = filename
        self.deps = set({})


class SectionSymbol (Symbol, Dependency):
    def __init__(self, filename, *args):
        Symbol.__init__ (self, *args)
        Dependency.__init__ (self, filename)
        self.symbols = []
        self.sections = []
        self.functions = []
        self.signals = []
        self.vfunctions = []
        self.properties = []
        self.fields = []
        self.constants = []
        self.function_macros = []
        self.enums = []
        self.callbacks = []
        self.aliases = []
        self.records = []
        self.parsed_contents = None
        self.__list_map = {
                            FunctionSymbol: self.functions,
                            SignalSymbol: self.signals,
                            VirtualFunctionSymbol: self.vfunctions,
                            PropertySymbol: self.properties,
                            FieldSymbol: self.fields,
                            ConstantSymbol: self.constants,
                            FunctionMacroSymbol: self.function_macros,
                            EnumSymbol: self.enums,
                            CallbackSymbol: self.callbacks,
                            AliasSymbol: self.aliases,
                            RecordSymbol: self.records,
                            }


    def do_format (self):
        for symbol in self.symbols:
            if symbol.do_format ():
                symbol_list = self.__list_map [type (symbol)]
                symbol_list.append (symbol)
        return Symbol.do_format(self)

    def add_symbol (self, symbol):
        self.symbols.append (symbol)

    def get_short_description (self):
        if not self._comment:
            return ""
        if not self._comment.short_description:
            return ""
        return self._comment.short_description

class ClassSymbol (SectionSymbol):
    def __init__(self, *args):
        SectionSymbol.__init__(self, *args)
        self.__class_record = None

    def add_symbol (self, symbol):
        # Special case
        if type (symbol) == RecordSymbol:
            if self.ast_node:
                if str(symbol.ast_node.is_gtype_struct_for) == self.ast_node.gi_name:
                    self.__class_record = symbol
                return
        SectionSymbol.add_symbol (self, symbol)

    def do_format (self):
        if self.__class_record:
            self.__class_record.do_format ()

        return SectionSymbol.do_format (self)

    def get_class_doc (self):
        if self.__class_record:
            return self.__class_record.formatted_doc
        return None


def __add_symbols (symbols_node, type_name, class_node, name_formatter):
    added_symbols = 0
    if hasattr (class_node, type_name):
        for symbol in getattr (class_node, type_name):
            name = name_formatter.get_full_node_name (symbol)
            existing = symbols_node.xpath('SYMBOL[text()="%s"]' % name)
            if existing:
                continue
            new_element = etree.Element ('SYMBOL')
            new_element.text = name
            symbols_node.append (new_element)
            added_symbols += 1

    return added_symbols


def add_missing_symbols (transformer, sections):
    name_formatter = NameFormatter(language='C')
    symbol_resolver = SymbolResolver (transformer)
    sections_parser = SectionsParser (symbol_resolver, sections)
    added_signals = 0
    added_properties = 0
    added_virtual_methods = 0
    added_fields = 0
    added_functions = 0
    for name, section in sections_parser.get_class_sections ().iteritems():
        class_node = symbol_resolver.resolve_type (section.find ('TITLE').text)
        symbols_node = section.find ('SYMBOLS')
        added_functions += __add_symbols (symbols_node, 'methods', class_node, name_formatter)
        added_signals += __add_symbols (symbols_node, 'signals', class_node, name_formatter)
        added_properties += __add_symbols (symbols_node, 'properties', class_node, name_formatter)
        added_virtual_methods += __add_symbols (symbols_node, 'virtual_methods',
                class_node, name_formatter)
        added_fields += __add_symbols (symbols_node, 'fields',
                class_node, name_formatter)
        for symbol_node in symbols_node.findall('SYMBOL'):
            node = symbol_resolver.resolve_type (symbol_node.text)
            if type(node) == ast.Record:
                gtype_struct_for = str (node.is_gtype_struct_for)
                giname = str (class_node.gi_name)
                if gtype_struct_for == giname:
                    added_fields += __add_symbols (symbols_node, 'fields',
                        node, name_formatter)

    print "added %d signals" % added_signals
    print "added %d properties" % added_properties
    print "added %d virtual" % added_virtual_methods
    print "added %d fields" % added_fields
    print "added %d functions" % added_functions
    sections_parser.write ('fixed.xml')


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
                                link = LocalLink (symbol_name,
                                        self.__current_section.link.pagename,
                                        symbol_name)
                                self.local_links[symbol_name] = link
                                sym.set_link (link)
                                self.__current_section.add_symbol (sym)
                                self.__current_section.deps.add('"%s"' % comment_block.position.filename)
                                self.__current_section.deps.add('"%s"' %
                                        str(symbol.location.file))

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
        section = ClassSymbol (filename, symbol, comment, self.__doc_formatter)

        if self.__current_section:
            self.__current_section.sections.append (section)
        else:
            self.sections.append (section)

        self.__current_section = section
        pagename = "%s.%s" % (name, "html")
        link = LocalLink (None, pagename, name)
        self.local_links[name] = link
        self.__current_section.set_link (link)

        with open (path, 'r') as f:
            contents = f.read()
            res = self.filter_text (contents)

        self.dag.add ('"%s"' % os.path.basename(filename), list(self.__current_section.deps))
        return True

    def create_symbols (self, filename):
        self.parse_file (filename)
        self.dag.dot("dependencies.dot")

class Formatter(object):
    def __init__ (self, symbols, comments, include_directories, index_file, output,
            do_class_aggregation=False):
        self.__include_directories = include_directories
        self.__do_class_aggregation = do_class_aggregation
        self.__output = output
        self.__index_file = index_file
        self.__symbols = symbols
        self.__comments = comments

        self.__link_resolver = LinkResolver ()
        self.__name_formatter = NameFormatter(language='C')
        self.__symbol_factory = SymbolFactory (self)
        self.__local_links = {}
        self.__gnome_markdown_filter = GnomeMarkdownFilter (os.path.dirname(index_file))
        self.__gnome_markdown_filter.set_formatter (self)

        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}
 
    def create_symbols(self):
        n = datetime.now()
        sf = SectionFilter (os.path.dirname(self.__index_file), self.__symbols,
                self.__comments, self, self.__symbol_factory)
        sf.create_symbols (os.path.basename(self.__index_file))
        self.__local_links = sf.local_links
        print "Markdown parsing done", datetime.now() - n
        return sf.sections

        filename = os.path.basename (self.__index_file)
        dir_ = os.path.dirname (self.__index_file)
        sf = SectionFilter (dir_, self.__symbol_resolver, self.__symbol_factory,
                self)
        sf.create_symbols (filename)
        self.__local_links = sf.local_links
        return sf.sections

    def __format_section (self, section):
        out = ""
        section.do_format ()
        filename = "%s.%s" % (os.path.splitext(section.filename)[0],
                self._get_extension())
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
        #self.format_index (sections, output)

    def format_index (self, sections, output):
        out = self._format_index (sections)

        extension = self._get_extension ()
        filename = os.path.join (output, "index.%s" % extension)
        if out:
            with open (filename, 'w') as f:
                f.write (unicode(out).encode('utf-8'))

    def __create_local_link (self, containing_page_name, node_name):
            return LocalLink (node_name, containing_page_name, node_name)

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

    def _format_index (self, pages):
        """
        Called to format an index
        @filenames: the files that have been produced by the parsing
        @pages: The different pages for the underlying sections
        """
        self.__warn_not_implemented (self._format_index)
        return ""
