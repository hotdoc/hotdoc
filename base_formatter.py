# -*- coding: utf-8 -*-

import os, re

from xml.etree import ElementTree as ET
from giscanner import ast
import logging
from lxml import etree

from xml.sax.saxutils import unescape

from datetime import datetime

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

    def make_gtkdoc_id(self, node, separator=None, formatter=None):
        def class_style(name):
            return name

        def function_style(name):
            snake_case = re.sub('(.)([A-Z][a-z]+)', r'\1_\2',
                    name)
            snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_case).lower()
            return snake_case.replace("_", "-")

        if separator is None:
            separator = "-"
            formatter = function_style
            if isinstance(node, (ast.Class, ast.Union, ast.Enum, ast.Record, ast.Interface,
                                ast.Callback, ast.Alias)):
                separator = ""
                formatter = class_style

        if isinstance(node, ast.Namespace):
            if node.identifier_prefixes:
                return formatter(node.identifier_prefixes[0])
            return node.name

        if hasattr(node, '_chain') and node._chain:
            parent = node._chain[-1]
        else:
            parent = getattr(node, 'parent', None)

        if parent is None:
            if isinstance(node, ast.Function) and node.shadows:
                return '%s%s%s' % (formatter(node.namespace.name), separator,
                        formatter(node.shadows))
            else:
                return '%s%s%s' % (formatter(node.namespace.name), separator,
                        formatter(node.name))

        if isinstance(node, ast.Function) and node.shadows:
            return '%s%s%s' % (self.make_gtkdoc_id(parent, separator=separator,
                formatter=formatter), separator, formatter(node.shadows))
        else:
            return '%s%s%s' % (self.make_gtkdoc_id(parent, separator=separator,
                formatter=formatter), separator, formatter(node.name))

    def make_page_name (self, node):
        return self.__make_c_node_name (node)

class DocScanner(object):
    def __init__(self):
        specs = [
            ('!alpha', r'[a-zA-Z0-9_]+'),
            ('!alpha_dash', r'[a-zA-Z0-9_-]+'),
            ('!anything', r'.*'),
            ('note', r'\>\s*<<note_contents:anything>>\s*\n'),
            ('new_paragraph', r'\n\n'),
            ('new_line', r'\n'),
            ('code_start_with_language',
                r'\|\[\<!\-\-\s*language\s*\=\s*\"<<language_name:alpha>>\"\s*\-\-\>'),
            ('code_start', r'\|\['),
            ('code_end', r'\]\|'),
            ('property', r'#<<type_name:alpha>>:(<<property_name:alpha_dash>>)'),
            ('signal', r'#<<type_name:alpha>>::(<<signal_name:alpha_dash>>)'),
            ('type_name', r'#(<<type_name:alpha>>)'),
            ('enum_value', r'%(<<member_name:alpha>>)'),
            ('parameter', r'@<<param_name:alpha>>'),
            ('function_call', r'<<symbol_name:alpha>>\s*\(\)'),
            ('include', r'{{\s*<<include_name:anything>>\s*}}'),
            ('heading', r'#+\s+<<heading:anything>>'),
        ]
        self.specs = self.unmangle_specs(specs)
        self.regex = self.make_regex(self.specs)

    def unmangle_specs(self, specs):
        mangled = re.compile('<<([a-zA-Z_:]+)>>')
        specdict = dict((name.lstrip('!'), spec) for name, spec in specs)

        def unmangle(spec, name=None):
            def replace_func(match):
                child_spec_name = match.group(1)

                if ':' in child_spec_name:
                    pattern_name, child_spec_name = child_spec_name.split(':', 1)
                else:
                    pattern_name = None

                child_spec = specdict[child_spec_name]
                # Force all child specs of this one to be unnamed
                unmangled = unmangle(child_spec, None)
                if pattern_name and name:
                    return '(?P<%s_%s>%s)' % (name, pattern_name, unmangled)
                else:
                    return unmangled

            return mangled.sub(replace_func, spec)

        return [(name, unmangle(spec, name)) for name, spec in specs]

    def make_regex(self, specs):
        regex = '|'.join('(?P<%s>%s)' % (name, spec) for name, spec in specs
                         if not name.startswith('!'))
        return re.compile(regex)

    def get_properties(self, name, match):
        groupdict = match.groupdict()
        properties = {name: groupdict.pop(name)}
        name = name + "_"
        for group, value in groupdict.iteritems():
            if group.startswith(name):
                key = group[len(name):]
                properties[key] = value
        return properties

    def scan(self, text):
        pos = 0
        while True:
            match = self.regex.search(text, pos)
            if match is None:
                break

            start = match.start()
            if start > pos:
                yield ('other', text[pos:start], None)

            pos = match.end()
            name = match.lastgroup
            yield (name, match.group(0), self.get_properties(name, match))

        if pos < len(text):
            yield ('other', text[pos:], None)


# Long name is long
def get_sorted_symbols_from_sections (sections, symbols):
    for element in sections:
        if element.tag == "SYMBOL":
            symbols.append (element.text)
        get_sorted_symbols_from_sections (element, symbols)


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
        self.__pagename = pagename

    def get_link (self):
        if (self.__symbol):
            return "%s#%s" % (self.__pagename, self.__symbol)
        else:
            return self.__pagename

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

    def make_qualified_symbol (self, node):
        if not hasattr (node, "type"): # Aliases
            type_ = node.target
        else:
            type_ = node.type
        res = None

        qualifiers = ""
        type_name = ""
        indirection = ""
        link = ""

        if type_.target_fundamental:
            qualifiers, type_name, indirection = self.__split_ctype (type_.ctype)
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

    def __repr__(self):
        res = "%s\n" % object.__repr__(self)
        res += "%s %s %s %s\n" % (self.qualifiers, self.type_name,
                self.indirection, self.argname)
        if self.link:
            res += "[%s]\n" % self.link.get_link ()
        else:
            res += "No link !"
        res += "Description : \n%s\n" % self.formatted_doc
        return res

    def do_format (self):
        self.formatted_doc = self.__doc_formatter.format_doc (self.ast_node)
        return True

    def set_link (self, link):
        self.link = link

    def get_extra_links (self):
        return []

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
        return [member.type_name for member in self.members]

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
    pass


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


class FunctionSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.parameters = []
        self.return_value = None

    def __repr__ (self):
        res = "%s\n" % Symbol.__repr__(self)
        res += "===\nParameters :\n"
        for param in self.parameters:
            res += param.__repr__() + "\n"
        if self.return_value:
            res += "===\nReturn value :\n%s" % self.return_value.__repr__()

        return res

    def do_format (self):
        self.return_value = self._symbol_factory.make_qualified_symbol (self.ast_node.retval)
        for parameter in self.ast_node.all_parameters:
            param = self._symbol_factory.make_qualified_symbol (parameter)
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
        self.__class_record = None
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
                            }

    def add_symbol (self, symbol):
        # Special case
        if type (symbol) == RecordSymbol:
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
        if not self.ast_node.short_description:
            return ""
        return self.ast_node.short_description

    def __repr__(self):
        res = "%s\n" % Symbol.__repr__(self)
        res += "===\nFunctions :\n"
        for func in self.functions:
            res += func.__repr__()

        res += "\n"
        return res

    def get_class_doc (self):
        if self.__class_record:
            return self.__class_record.formatted_doc
        return None


class SectionsParser(object):
    def __init__(self, symbol_resolver):
        self.__symbol_resolver = symbol_resolver
        parser = etree.XMLParser(remove_blank_text=True)
        self.__root = etree.parse ('tmpsections.xml', parser)
        self.__name_formatter = NameFormatter (language='C')
        self.__class_sections = {}

    def __find_class_sections (self):
        for section in self.__root.findall ('.//SECTION'):
            name = section.find('SYMBOL').text
            if type (self.__symbol_resolver.resolve_type (name)) in [ast.Class,
                    ast.Record, ast.Interface]:
                self.__class_sections[name] = section

    def get_sections (self, parent=None):
        if not parent:
            return self.__root.findall('SECTION')
        else:
            return parent.findall('SECTION')

    def get_class_sections (self):
        if not self.__class_sections:
            self.__find_class_sections ()
        return self.__class_sections

    def get_all_sections (self):
        return self.__sections

    def write (self, filename):
        self.__root.write (filename, pretty_print=True, xml_declaration=True)

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


def add_missing_symbols (transformer):
    name_formatter = NameFormatter(language='C')
    symbol_resolver = SymbolResolver (transformer)
    sections_parser = SectionsParser (symbol_resolver)
    added_signals = 0
    added_properties = 0
    added_virtual_methods = 0
    added_fields = 0
    added_functions = 0
    for name, section in sections_parser.get_class_sections ().iteritems():
        class_node = symbol_resolver.resolve_type (section.find ('SYMBOL').text)
        print section.find ('SYMBOL').text
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

class Formatter(object):
    def __init__ (self, transformer, include_directories, sections, output,
            do_class_aggregation=False):
        self.__transformer = transformer
        self.__include_directories = include_directories
        self.__sections = sections
        self.__do_class_aggregation = do_class_aggregation
        self.__output = output

        self.__doc_formatters = self.__create_doc_formatters ()
        self.__doc_scanner = DocScanner()
        self.__link_resolver = LinkResolver (transformer)
        self.__symbol_resolver = SymbolResolver (self.__transformer)
        self.__name_formatter = NameFormatter(language='C')
        self.__sections_parser = SectionsParser (self.__symbol_resolver)
        self.__symbol_factory = SymbolFactory (self, self.__symbol_resolver,
                self.__transformer)
        self.__local_links = {}

        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}

        # Used to avoid parsing code as doc
        self.__processing_code = False

        # Used to create the index file and aggregate pages  if required
        self.__created_pages = {}
 
    def __create_symbols (self):
        section_nodes = self.__sections_parser.get_sections ()
        sections = []
        for section_node in section_nodes:
            section_name = section_node.find ('SYMBOL').text
            class_node = self.__symbol_resolver.resolve_type (section_name)

            if type (class_node) not in [ast.Class, ast.Record, ast.Interface,
                    ast.Enum]:
                #FIXME
                #print "didn't handle %s" % str(type (class_node))
                continue

            section = ClassSymbol (class_node, self, section_name)
            pagename = os.path.basename (self.__make_file_name (class_node))
            link = self.__create_local_link (pagename, None)
            self.__local_links[section_name] = link
            symbols = section_node.find ('SYMBOLS').findall ('SYMBOL')
            for symbol_node in symbols:
                ast_node = self.__symbol_resolver.resolve_symbol (symbol_node.text)
                if not ast_node:
                    ast_node = self.__symbol_resolver.resolve_type (symbol_node.text)

                symbol = self.__symbol_factory.make (ast_node, symbol_node.text)
                if not symbol:
                    #FIXME
                    continue

                link = self.__create_local_link (pagename, symbol.type_name)
                symbol.set_link (link)
                for linkname in symbol.get_extra_links():
                    link = self.__create_local_link (pagename, linkname)
                    self.__local_links[linkname] = link

                section.add_symbol (symbol)
                self.__local_links[symbol.type_name] = link
            sections.append (section)

        return sections

    def format (self, output):
        n = datetime.now ()
        sections = self.__create_symbols ()
        for section in sections:
            section.do_format ()
            filename = self.__make_file_name (section.ast_node)
            with open (filename, 'w') as f:
                out = self._format_class (section, True)
                f.write (out.encode('utf-8'))

    def format_index (self, output):
        return ""
        out = ""

        sections = self.__sections_parser.get_sections ()
        pages = []
        for section in sections:
            try:
                page = self.__created_pages[section.find ('SYMBOL').text]
            except KeyError:
                #FIXME
                continue
            pages.append (page)

        out += self._format_index (pages)

        extension = self._get_extension ()
        filename = os.path.join (output, "index.%s" % extension)
        if out:
            with open (filename, 'w') as f:
                f.write (unicode(out).encode('utf-8'))

    def __create_doc_formatters (self):
        return {
            'other': self.__format_other,
            'property': self.__format_property,
            'signal': self.__format_signal,
            'type_name': self.__format_type_name,
            'enum_value': self.__format_enum_value,
            'parameter': self.__format_parameter,
            'function_call': self.__format_function_call,
            'code_start': self.__format_code_start,
            'code_start_with_language': self.__format_code_start_with_language,
            'code_end': self.__format_code_end,
            'new_line': self.__format_new_line,
            'new_paragraph': self.__format_new_paragraph,
            'include': self.__format_include,
            'note': self.__format_note,
            'heading': self.__format_heading
        }

    def __format_other (self, node, match, props):
        if self.__processing_code:
            match += '\n'
        return self._format_other (match)

    def __format_property (self, node, match, props):
        type_node = self.__symbol_resolver.resolve_type(props['type_name'])
        if type_node is None:
            return match

        try:
            prop = self._find_thing(type_node.properties, props['property_name'])
        except (AttributeError, KeyError):
            return self.__format_other (node, match, props)

        return self._format_property (node, prop)

    def __format_signal (self, node, match, props):
        raise NotImplementedError

    def __create_local_link (self, containing_page_name, node_name):
            return LocalLink (node_name, containing_page_name)

    def get_named_link(self, ident):
        link = None
        try:
            link = self.__local_links [ident]
        except KeyError:
            link = self.__link_resolver.get_named_link (ident)
        return link

    def __format_type_name (self, node, match, props):
        ident = props['type_name']
        link = self.get_named_link (ident)
        return self._format_type_name (ident, link)

    def __format_enum_value (self, node, match, props):
        raise NotImplementedError

    def __format_parameter (self, node, match, props):
        try:
            parameter = node.get_parameter(props['param_name'])
        except (AttributeError, ValueError):
            return self.__format_other (node, match, props)
 
        if isinstance(parameter.type, ast.Varargs):
            param_name = "..."
        else:
            param_name = parameter.argname

        return self._format_parameter (param_name)

    def __format_function_call (self, node, match, props):
        ident = props['symbol_name']
        link = self.get_named_link (ident)
        if not link:
            return self.__format_other (node, match, props)

        return self._format_function_call (ident, link)

    def __format_code_start (self, node, match, props):
        self.__processing_code = True
        return self._format_code_start ()

    def __format_code_start_with_language (self, node, match, props):
        self.__processing_code = True
        return self._format_code_start_with_language (props["language_name"])

    def __format_code_end (self, node, match, props):
        self.__processing_code = False
        return self._format_code_end ()

    def __format_new_line (self, node, match, props):
        if self.__processing_code:
            return ""

        return self._format_new_line ()

    def __format_new_paragraph (self, node, match, props):
        return self._format_new_paragraph ()

    def __format_include (self, node, match, props):
        filename = props["include_name"].strip()
        f = None

        try:
            f = open(filename, 'r')
        except IOError:
            for dir_ in self.__include_directories:
                try:
                    f = open(os.path.join(dir_, filename), 'r')
                    break
                except:
                    continue
        if f:
            contents = f.read()
            if self.__processing_code:
                return self._format_other (contents)
            else:
                out = self.__format_doc_string(node, contents)
            f.close()
        else:
            logging.warning("Could not find file %s" % (props["include_name"], ))
            out = match

        return out

    def __format_note (self, node, match, props):
        if self.__processing_code:
            return self.__format_other (node, match, props)

        return self._format_note (props["note_contents"])

    def __format_heading (self, node, match, props):
        return self._format_heading ()

    def __make_file_name (self, node):
        extension = self._get_extension ()
        name = self.__name_formatter.make_page_name (node)
        if not name:
            return ""
        return os.path.join (self.__output, "%s.%s" % (name, extension))

    def __format_doc_string (self, node, docstring):
        if not docstring:
            return ""

        out = ""
        docstring = unescape (docstring)
        tokens = self.__doc_scanner.scan (docstring)
        for tok in tokens:
            kind, match, props = tok
            try:
                formated_token = self.__doc_formatters[kind](node, match, props)
                if formated_token:
                    out += formated_token
            except NotImplementedError:
                continue

        return out

    def format_doc (self, node):
        out = ""
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

    def _format_other (self, other):
        """
        @other: A string that doesn't contain any GNOME markup
        """
        self.__warn_not_implemented (self._format_other)
        return ""

    def _format_type_name (self, type_name, link):
        """
        @type_name: the name of a type to link to
        @link: the prepared link
        """
        self.__warn_not_implemented (self._format_type_name)
        return ""

    def _format_parameter (self, param_name):
        """
        @param_name: the name of a parameter referred to
        """
        self.__warn_not_implemented (self._format_parameter)
        return ""

    def _format_new_paragraph (self):
        """
        Called when the parsed markup contained a new paragraph
        """
        self.__warn_not_implemented (self._format_new_paragraph)
        return ""

    def _format_heading (self):
        """
        """
        self.__warn_not_implemented (self._format_heading)
        return ""

    def _format_function_call (self, function_name, link):
        """
        @function_name: A function name to link to
        @link: the prepared link
        """
        self.__warn_not_implemented (self._format_function_call)
        return ""

    def _format_new_line (self):
        """
        Called when the parsed markup contained a new line
        """
        self.__warn_not_implemented (self._format_new_line)
        return ""

    def _format_note (self, note):
        """
        @note: A note to format, eg an informational hint
        """
        self.__warn_not_implemented (self._format_note)
        return ""

    def _format_code_start (self):
        """
        Called when the parsed markup contains code to format,
        with no specified language
        """
        self.__warn_not_implemented (self._format_code_start)
        return ""

    def _format_code_start_with_language (self, language):
        """
        Called when the parsed markup contains code to format
        @language: the language of the code
        """
        self.__warn_not_implemented (self._format_code_start_with_language)
        return ""

    def _format_code_end (self):
        """
        Called when a code block is finished
        """
        self.__warn_not_implemented (self._format_code_end)
        return ""

    def _format_index (self, pages):
        """
        Called to format an index
        @filenames: the files that have been produced by the parsing
        @pages: The different pages for the underlying sections
        """
        self.__warn_not_implemented (self._format_index)
        return ""
