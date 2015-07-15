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
        self.__gtk_doc_links = self.__gather_gtk_doc_links ()

    def __gather_gtk_doc_links (self):
        links = dict ({})

        if not os.path.exists(os.path.join("/usr/share/gtk-doc/html")):
            print "no gtk doc to look at"
            return

        for node in os.listdir(os.path.join(DATADIR, "gtk-doc", "html")):
            dir_ = os.path.join(DATADIR, "gtk-doc/html", node)
            if os.path.isdir(dir_):
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
                    symbol_map[split_line[1]] = link

        return symbol_map

    def get_link (self, node):
        # Kind of a hack
        if hasattr (node, "target_fundamental") and node.target_fundamental:
            try:
                stripped_name = re.sub('const', '', node.ctype)
                stripped_name = re.sub('\*', '', stripped_name).strip()
                link = self.__gtk_doc_links['glib'][stripped_name]
            except KeyError:
                link = None
            return link

        gtk_doc_identifier = self.__name_formatter.make_gtkdoc_id(node)
        if isinstance(node, (ast.Constant, ast.Member)):
            gtk_doc_identifier = gtk_doc_identifier.upper() + ":CAPS"

        package_links = None
        for package in node.namespace.exported_packages:
            try:
                package_links = self.__gtk_doc_links[package]
            except KeyError:
                package = re.sub(r'\-[0-9]+\.[0-9]+$', '', package)
                try:
                    package_links = self.__gtk_doc_links[package]
                except KeyError:
                    continue

        if not package_links:
            return None

        try:
            link = package_links[gtk_doc_identifier]
        except KeyError:
            return None

        return link


class Symbol (object):
    def __init__(self, type_name, qualifiers, indirection, argname, link, ast_node, formatted_doc):
        self.type_name = type_name
        self.argname = argname
        self.qualifiers = qualifiers
        self.indirection = indirection
        self.link = link
        self.ast_node = ast_node
        self.formatted_doc = formatted_doc

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


class EnumSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.members = []

    def add_member (self, member):
        self.members.append (member)


class PropertySymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.type_ = None

    def set_type (self, type_):
        self.type_ = type_

class AliasSymbol (PropertySymbol):
    pass

class FieldSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.type_ = None

    def set_type (self, type_):
        self.type_ = type_

class ConstantSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.value = None

    def set_value (self, value):
        self.value = value

class FunctionSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.parameters = []
        self.return_value = None

    def add_parameter (self, parameter):
        self.parameters.append (parameter)

    def __repr__ (self):
        res = "%s\n" % Symbol.__repr__(self)
        res += "===\nParameters :\n"
        for param in self.parameters:
            res += param.__repr__() + "\n"
        if self.return_value:
            res += "===\nReturn value :\n%s" % self.return_value.__repr__()

        return res

class FunctionMacroSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
        self.parameters = []

    def add_parameter (self, parameter):
        self.parameters.append (parameter)

class ClassSymbol (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)
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
        self.class_doc = None

    def add_function (self, func):
        self.functions.append (func)

    def add_signal (self, signal):
        self.signals.append (signal)

    def add_vfunction (self, vfunction):
        self.vfunctions.append (vfunction)

    def add_callback (self, callback):
        self.callbacks.append (callback)

    def add_property (self, prop):
        self.properties.append (prop)

    def add_alias (self, alias):
        self.aliases.append (alias)

    def add_constant (self, constant):
        self.constants.append (constant)

    def add_field (self, field):
        self.fields.append (field)

    def add_function_macro (self, func):
        self.function_macros.append (func)

    def add_enum (self, enum):
        self.enums.append (enum)

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

class Parameter (Symbol):
    def __init__(self, *args):
        Symbol.__init__(self, *args)

class SectionsParser(object):
    def __init__(self, symbol_resolver):
        n = datetime.now()
        self.__symbol_resolver = symbol_resolver
        parser = etree.XMLParser(remove_blank_text=True)
        self.__root = etree.parse ('tmpsections.xml', parser)
        self.__name_formatter = NameFormatter (language='C')
        self.__symbols = {}
        #self.__create_symbols ()
        #self.__sections = self.__root.findall('.//SECTION')
        self.__class_sections = {}
        print "section parsing : ", datetime.now() - n

    def __find_class_sections (self):
        for section in self.__root.findall ('.//SECTION'):
            name = section.find('SYMBOL').text
            if type (self.__symbol_resolver.resolve_type (name)) in [ast.Class,
                    ast.Record, ast.Interface]:
                self.__class_sections[name] = section

    def symbol_is_in_class_section (self, symbol):
        parent = symbol.getparent().getparent()
        name_node = parent.find ('SYMBOL')
        if name_node is None:
            return False

        # FIXME special case for simple translation script
        if name_node.text == symbol.text:
            return False
        return name_node.text in self.__class_sections

    def __create_symbols (self):
        for symbol_node in self.__root.findall('.//SYMBOL'):
            section_node = symbol_node.getparent().getparent()
            ast_node = self.__symbol_resolver.resolve_symbol (symbol_node.text)
            if not ast_node:
                ast_node = self.__symbol_resolver.resolve_type (symbol_node.text)

            symbol = None
            if type (ast_node) == ast.Function:
                symbol = FunctionSymbol (symbol_node.text, section_node, ast_node)
            if symbol:
                self.__symbols[symbol_node.text] = symbol

    def get_all_symbols (self):
        return self.__symbols

    def find_symbol (self, symbol):
        name = self.__name_formatter.get_full_node_name (symbol)
        try:
            return self.__symbols[name]
        except KeyError:
            return None

    def get_sections (self, parent=None):
        if not parent:
            return self.__root.findall('SECTION')
        else:
            return parent.findall('SECTION')

    def get_class_section (self, class_node):
        node_name = self.__name_formatter.get_full_node_name (class_node)
        try:
            return self.__class_sections[node_name]
        except KeyError:
            return None

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
            print "new element :", name
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

        self.__handlers = self.__create_handlers ()
        self.__doc_formatters = self.__create_doc_formatters ()
        self.__doc_scanner = DocScanner()
        self.__link_resolver = LinkResolver (transformer)
        self.__symbol_resolver = SymbolResolver (self.__transformer)
        self.__name_formatter = NameFormatter(language='C')
        self.__sections_parser = SectionsParser (self.__symbol_resolver)

        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}

        # Used to avoid parsing code as doc
        self.__processing_code = False

        # Used to create the index file and aggregate pages  if required
        self.__created_pages = {}
 
    def format (self, output):
        n = datetime.now ()
        sections = self.__sections_parser.get_sections ()
        for section_node in sections:
            section_name = section_node.find ('SYMBOL').text
            class_node = self.__symbol_resolver.resolve_type (section_name)
            self.__current_section_node = class_node

            if type (class_node) not in [ast.Class, ast.Record, ast.Interface]:
                #FIXME
                #print "didn't handle %s" % str(type (class_node))
                continue

            doc = self.__format_doc (class_node)
            klass = ClassSymbol ('', '', '', section_name, self.__get_link
                    (class_node), class_node, doc)
            symbols = section_node.find ('SYMBOLS').findall ('SYMBOL')
            for symbol_node in symbols:
                ast_node = self.__symbol_resolver.resolve_symbol (symbol_node.text)
                if not ast_node:
                    ast_node = self.__symbol_resolver.resolve_type (symbol_node.text)

                if not ast_node:
                    #FIXME
                    continue

                try:
                    handler = self.__handlers [type (ast_node)]
                except KeyError:
                    #FIXME
                    #print "didn't handle symbol %s" % symbol_node.text
                    print type (ast_node), symbol_node.text, section_name
                    continue

                handler (klass, symbol_node, ast_node)

            filename = self.__make_file_name (class_node)
            with open (filename, 'w') as f:
                out = self._format_class (klass, True)
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

    def __create_handlers (self):
        return {
                ast.Function: self.__handle_function,
                ast.VFunction: self.__handle_vfunction,
                ast.FunctionMacro: self.__handle_function_macro,
                ast.Signal: self.__handle_signal,
                ast.Property: self.__handle_property,
                ast.Field: self.__handle_field,
                ast.Constant: self.__handle_constant,
                ast.Record: self.__handle_record,
                ast.Enum: self.__handle_enum,
                ast.Bitfield: self.__handle_enum,
                ast.Callback: self.__handle_callback,
                ast.Alias: self.__handle_alias,
               }

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

    def __get_link (self, node, is_aggregated=False):
        link = None
        if hasattr (node, "namespace") and node.namespace == self.__transformer.namespace:
            if self.__do_class_aggregation and is_aggregated:
                pagename = self.__make_file_name (self.__current_section_node)
            else:
                pagename = self.__make_file_name (node)

            if pagename:
                pagename = os.path.basename (pagename)
                link = LocalLink (self.__name_formatter.get_full_node_name
                        (node), pagename)
        else:
            link = self.__link_resolver.get_link (node)

        return link

    def __format_type_name (self, node, match, props):
        ident = props['type_name']
        type_ = self.__symbol_resolver.resolve_type(ident)

        if not type_:
            return self.__format_other (node, match, props)

        link = self.__get_link (type_)

        type_name = self.__name_formatter.get_full_node_name (type_)

        return self._format_type_name (type_name, link)

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
        func = self.__symbol_resolver.resolve_symbol(props['symbol_name'])
        if func is None:
            return self.__format_other (node, match, props)

        function_name = self.__name_formatter.get_full_node_name (func)
        link = self.__get_link (func)

        return self._format_function_call (function_name, link)

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

    def __format_doc (self, node):
        out = ""
        out += self.__format_doc_string (node, node.doc)
        return out

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

    def __create_linked_symbol (self, node):
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
            link = self.__get_link (type_)
        elif type_.ctype is not None:
            qualifiers, type_name, indirection = self.__split_ctype (type_.ctype)
            type_node = self.__symbol_resolver.resolve_type (type_name)
            if type_node:
                link = self.__get_link (type_node)
        else:
            type_node = self.__transformer.lookup_giname (type_.target_giname)
            type_name = type_node.ctype
            if type_node:
                link = self.__get_link (type_node)
            indirection = '*'

        if not type_name:
            #FIXME
            print "lol", node
            return None

        doc = self.__format_doc (node)

        if type (node) == ast.Parameter:
            argname = node.argname
        else:
            argname = None

        return Symbol (type_name, qualifiers, indirection, argname, link, node, doc)

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

    def __handle_callable (self, symbol_node, actual_name, ast_node):
        doc = self.__format_doc (ast_node)
        func = FunctionSymbol (actual_name, '', '', '', self.__get_link
                (ast_node, True), ast_node, doc)

        func.return_value = self.__create_linked_symbol (ast_node.retval)
        for parameter in ast_node.all_parameters:
            param = self.__create_linked_symbol (parameter)
            func.add_parameter (param)

        return func

    def __handle_function (self, klass, symbol_node, ast_node):
        klass.add_function (self.__handle_callable (symbol_node,
            symbol_node.text, ast_node))

    def __handle_function_macro (self, klass, symbol_node, ast_node):
        doc = self.__format_doc (ast_node)
        func = FunctionMacroSymbol (symbol_node.text, '', '', '',
                self.__get_link (ast_node, True), ast_node, doc)
        for parameter in ast_node.parameters:
            doc = self.__format_doc (parameter)
            param = Symbol (parameter.argname, '', '', '',
                    '', parameter, doc)
            func.add_parameter (param)
        klass.add_function_macro (func)

    def __handle_record (self, klass, symbol_node, ast_node):
        if str(ast_node.is_gtype_struct_for) == klass.ast_node.gi_name:
            klass.class_doc = self.__format_doc (ast_node)

    def __handle_alias (self, klass, symbol_node, ast_node):
        doc = self.__format_doc (ast_node)
        alias = AliasSymbol (symbol_node.text, '', '', '',
                self.__get_link (ast_node, True), ast_node, doc)
        type_ = self.__create_linked_symbol (ast_node)
        alias.set_type (type_)
        klass.add_alias (alias)

    def __handle_enum (self, klass, symbol_node, ast_node):
        doc = self.__format_doc (ast_node)
        enum = EnumSymbol (symbol_node.text, '', '', '',
                self.__get_link (ast_node, True), ast_node, doc)
        for member in ast_node.members:
            doc = self.__format_doc (member)
            member_ = Symbol (member.symbol, '', '', '', '', member, doc)
            enum.add_member (member_)
        klass.add_enum (enum)

    def __handle_callback (self, klass, symbol_node, ast_node):
        klass.add_callback (self.__handle_callable (symbol_node, symbol_node.text, ast_node))

    def __handle_vfunction (self, klass, symbol_node, ast_node):
        klass.add_vfunction (self.__handle_callable (symbol_node, ast_node.name, ast_node))

    def __handle_signal (self, klass, symbol_node, ast_node):
        self.__add_missing_signal_parameters (ast_node)

        klass.add_signal (self.__handle_callable (symbol_node, ast_node.name, ast_node))

    def __handle_property (self, klass, symbol_node, ast_node):
        doc = self.__format_doc (ast_node)
        type_ = self.__create_linked_symbol (ast_node)
        prop = PropertySymbol (ast_node.name, '', '', '', self.__get_link
                (ast_node, True), ast_node, doc)
        prop.set_type (type_)
        klass.add_property (prop)

    def __handle_constant (self, klass, symbol_node, ast_node):
        doc = self.__format_doc (ast_node)
        constant = ConstantSymbol (ast_node.ctype, '', '', '', self.__get_link
                (ast_node, True), ast_node, doc)
        constant.set_value (ast_node.value)
        klass.add_constant (constant)

    def __handle_field (self, klass, symbol_node, ast_node):
        if ast_node.type is None or ast_node.private:
            return

        doc = self.__format_doc (ast_node)
        type_ = self.__create_linked_symbol (ast_node)
        field = FieldSymbol (ast_node.name, '', '', '', self.__get_link
                (ast_node, True), ast_node, doc)
        field.set_type (type_)
        klass.add_field (field)

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
