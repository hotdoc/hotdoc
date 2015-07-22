# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import logging

from datetime import datetime
from lxml import etree
from giscanner import ast
from xml.sax.saxutils import unescape

from gnome_markdown_filter import GnomeMarkdownFilter
from pandoc_client import pandoc_converter
from pandocfilters import BulletList

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
    def __init__ (self, symbol, local_prefix, remote_prefix, filename):
        self.symbol = symbol
        self.local_prefix = local_prefix
        self.remote_prefix = remote_prefix
        self.filename = filename

    def get_link (self):
        return "%s/%s" % (self.remote_prefix, self.filename)


class LocalLink (Link):
    def __init__(self, symbol, pagename):
        self.__symbol = symbol
        self.pagename = pagename

    def get_link (self):
        if (self.__symbol):
            return "%s#%s" % (self.pagename, self.__symbol)
        else:
            return self.pagename


class LinkResolver(object):
    def __init__(self, transformer):
        self.__transformer = transformer
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
                    link = ExternalLink (split_line[1], dir_, remote_prefix,
                            filename)
                    self.__all_links[split_line[1].replace('-', '_')] = link

    def get_named_link (self, name):
        link = None
        try:
            link = self.__all_links[name]
        except KeyError:
            pass
        return link


class SymbolFactory (object):
    def __init__(self, doc_formatter, symbol_resolver, transformer):
        self.__doc_formatter = doc_formatter
        self.__symbol_resolver = symbol_resolver
        self.__transformer = transformer
        self.__symbol_classes = {
                    ast.Function: FunctionSymbol,
                    ast.FunctionMacro: FunctionMacroSymbol,
                    ast.VFunction: VirtualFunctionSymbol,
                    ast.Signal: SignalSymbol,
                    ast.Property: PropertySymbol,
                    ast.Field: FieldSymbol,
                    ast.Constant: ConstantSymbol,
                    ast.Record: RecordSymbol,
                    ast.Enum: EnumSymbol,
                    ast.Bitfield: EnumSymbol,
                    ast.Callback: CallbackSymbol,
                    ast.Alias: AliasSymbol,
                }

        self.__translations = {
                "utf8": "gchar *",
                "<map>": "GHashTable *",
                }

    def __split_ctype (self, ctype):
        qualifiers = ""
        type_name = ""
        indirection = ""
        indirection = ctype.count ('*') * '*'
        qualified_type = ctype.strip ('*')
        for token in qualified_type.split ():
            if token in ["const"]:
                if qualifiers:
                    qualifiers += " %s" % token
                else:
                    qualifiers += token
            else:
                type_name += token

        return (qualifiers, type_name, indirection)

    def __translate_fundamental (self, target):
        return self.__translations[target]

    def make_qualified_symbol (self, node):
        if not hasattr (node, "type"): # Aliases
            type_ = node.target
        else:
            type_ = node.type
        res = None

        qualifiers = ""
        type_name = ""
        indirection = ""
        array_indirection = ""
        link = ""

        while not type_.ctype and isinstance (type_, ast.Array):
            type_ = type_.element_type
            array_indirection += '*'

        if type_.target_fundamental:
            if not type_.ctype:
                ctype = self.__translate_fundamental (type_.target_fundamental)
            else:
                ctype = type_.ctype
            qualifiers, type_name, indirection = self.__split_ctype(ctype)
            link = self.__doc_formatter.get_named_link (type_name)
        elif type_.ctype is not None:
            qualifiers, type_name, indirection = self.__split_ctype (type_.ctype)
            type_node = self.__symbol_resolver.resolve_type (type_name)
            if type_node:
                link = self.__doc_formatter.get_named_link (type_name)
        else:
            type_node = self.__transformer.lookup_giname (type_.target_giname)
            type_name = type_node.ctype
            if type_node:
                link = self.__doc_formatter.get_named_link (type_name)
            indirection = '*'

        if not type_name:
            #FIXME
            print "lol", node
            return None

        if type (node) == ast.Parameter:
            argname = node.argname
        else:
            argname = None

        indirection += array_indirection
        symbol = QualifiedSymbol (qualifiers, indirection, argname, node,
                self.__doc_formatter, type_name)
        symbol.do_format ()
        symbol.set_link (link)
        return symbol

    def make_simple_symbol (self, node, name):
        symbol = Symbol (node, self.__doc_formatter, name, self)
        return symbol

    def make (self, ast_node, type_name=None):
        try:
            klass = self.__symbol_classes[type (ast_node)]
        except KeyError:
            return None

        return klass (ast_node, self.__doc_formatter, type_name, self)


class Symbol (object):
    def __init__(self, ast_node, doc_formatter, type_name, symbol_factory=None):
        self.ast_node = ast_node
        self.__doc_formatter = doc_formatter
        self._symbol_factory = symbol_factory
        self.type_name = type_name
        self.annotations = []
        self.flags = []
        self.filename = None

    def do_format (self):
        self.formatted_doc = self.__doc_formatter.format_doc (self.ast_node)
        return True

    def set_link (self, link):
        self.link = link

    def get_extra_links (self):
        return []

    def add_annotation (self, annotation):
        self.annotations.append (annotation)


class QualifiedSymbol (Symbol):
    def __init__(self, qualifiers, indirection, argname, *args):
        self.qualifiers = qualifiers
        self.indirection = indirection
        self.argname = argname
        Symbol.__init__(self, *args)


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
        self.parameters = []
        self.return_value = None

    def do_format (self):
        self.return_value = self._symbol_factory.make_qualified_symbol (self.ast_node.retval)

        if self.ast_node.instance_parameter:
            param = self._symbol_factory.make_qualified_symbol (self.ast_node.instance_parameter)
            self.parameters.append (param)

        for parameter in self.ast_node.parameters:
            param = self._symbol_factory.make_qualified_symbol (parameter)
            if type (self) == FunctionSymbol:
                if param.indirection:
                    if parameter.optional or parameter.nullable:
                        annotation = Annotation ("allow-none", "NULL is OK, both for passing and returning")
                        param.add_annotation(annotation)
                    if parameter.transfer == 'none':
                        annotation = Annotation ("transfer none", "Don't free data after the code is done")
                        param.add_annotation(annotation)
                    elif parameter.transfer == 'full':
                        annotation = Annotation ("transfer full", "Free data after the code is done")
                        param.add_annotation(annotation)
                if parameter.closure_name:
                    annotation = Annotation ("closure",
"This parameter is a closure for callbacks, many\
 bindings can pass NULL to %s" % parameter.closure_name)
                    param.add_annotation(annotation)
                if parameter.direction == "out":
                    annotation = Annotation ("out", "Parameter for returning results")
                    param.add_annotation(annotation)

            self.parameters.append (param)

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
        self.parameters = []

    def do_format (self):
        for parameter in self.ast_node.parameters:
            param = self._symbol_factory.make_simple_symbol (parameter,
                    parameter.argname)
            param.do_format()
            self.parameters.append (param)
        return Symbol.do_format(self)


class RecordSymbol (Symbol):
    pass


class SectionSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__ (self, *args)
        self.symbols = []
        self.sections = []

    def add_symbol (self, symbol):
        self.symbols.append (symbol)


class ClassSymbol (SectionSymbol):
    def __init__(self, *args):
        SectionSymbol.__init__(self, *args)
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
        self.__class_record = None
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
        for symbol in self.symbols:
            if symbol.do_format ():
                symbol_list = self.__list_map [type (symbol)]
                symbol_list.append (symbol)
        return SectionSymbol.do_format (self)

    def get_short_description (self):
        if not self.ast_node:
            return ""
        if not self.ast_node.short_description:
            return ""
        return self.ast_node.short_description

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
    def __init__(self, directory, symbol_resolver, symbol_factory, doc_formatter):
        GnomeMarkdownFilter.__init__(self, directory)
        self.sections = []
        self.__current_section = None
        self.__symbol_resolver = symbol_resolver
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
                    ast_node = self.__symbol_resolver.resolve_symbol (symbol_name)
                    if not ast_node:
                        ast_node = self.__symbol_resolver.resolve_type (symbol_name)

                    if ast_node:
                        symbol = self.__symbol_factory.make (ast_node, symbol_name)
                        if symbol:
                            link = LocalLink (symbol_name, self.__current_section.link.pagename)
                            self.local_links[symbol_name] = link
                            symbol.set_link (link)
                            self.__current_section.add_symbol (symbol)
                        continue

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
        ast_node = self.__symbol_resolver.resolve_type (name)

        section = ClassSymbol (ast_node, self.__doc_formatter,
            name)
        if self.__current_section:
            self.__current_section.sections.append (section)
        else:
            self.sections.append (section)
        self.__current_section = section
        pagename = "%s.%s" % (name, self.__doc_formatter._get_extension ())
        link = LocalLink (None, pagename)
        self.local_links[name] = link
        self.__current_section.set_link (link)

        with open (path, 'r') as f:
            contents = f.read()
            res = self.filter_text (contents)

        section.parsed_contents = res
        return True

    def create_symbols (self, filename):
        self.parse_file (filename)


class Formatter(object):
    def __init__ (self, transformer, include_directories, sections, index_file, output,
            do_class_aggregation=False):
        self.__transformer = transformer
        self.__include_directories = include_directories
        self.__sections = sections
        self.__do_class_aggregation = do_class_aggregation
        self.__output = output
        self.__index_file = index_file

        self.__link_resolver = LinkResolver (transformer)
        self.__symbol_resolver = SymbolResolver (self.__transformer)
        self.__name_formatter = NameFormatter(language='C')
        self.__symbol_factory = SymbolFactory (self, self.__symbol_resolver,
                self.__transformer)
        self.__local_links = {}
        self.__gnome_markdown_filter = GnomeMarkdownFilter (os.path.dirname(index_file))
        self.__gnome_markdown_filter.set_formatter (self)

        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}

        # Used to avoid parsing code as doc
        self.__processing_code = False

        # Used to create the index file and aggregate pages  if required
        self.__created_pages = {}
 
    def create_symbols(self):
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
        filename = section.link.pagename
        with open (os.path.join (self.__output, filename), 'w') as f:
            if section.parsed_contents and not section.ast_node:
                out += pandoc_converter.convert("json", "html", json.dumps
                        (section.parsed_contents))
            out += self._format_class (section, True)
            section.filename = os.path.basename(filename)
            f.write (out.encode('utf-8'))

        for section in section.sections:
            self.__format_section (section)

    def format (self, output):
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
            return LocalLink (node_name, containing_page_name)

    def get_named_link(self, ident, search_remote=True):
        link = None
        try:
            link = self.__local_links [ident]
        except KeyError:
            if search_remote:
                link = self.__link_resolver.get_named_link (ident)
        return link

    def __format_doc_string (self, node, docstring):
        if not docstring:
            return ""

        out = ""
        docstring = unescape (docstring)
        json_doc = self.__gnome_markdown_filter.filter_text (docstring)
        html_text = pandoc_converter.convert ("json", "html", json.dumps (json_doc))
        return html_text

    def format_doc (self, node):
        out = ""
        if node:
            out += self.__format_doc_string (node, node.doc)
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
