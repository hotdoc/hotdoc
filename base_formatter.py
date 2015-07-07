import os, re

from xml.etree import ElementTree as ET
from giscanner import ast
import logging

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

        if type (node) in (ast.Signal, ast.VFunction, ast.Property, ast.Field):
            out = "%s.%s-%s" % (node.namespace.name, node.parent.name,
                    node.name)

        if type (node) == ast.Function:
            while node:
                if out:
                    out = "%s.%s" % (node.name, out)
                else:
                    out = node.name

                if hasattr (node, "parent"):
                    node = node.parent
                else:
                    node = None

        elif type (node) in (ast.Class, ast.Enum):
            out = "%s.%s" % (node.namespace.name, node.name)

        return out

    def __make_c_node_name (self, node):
        out = ""
        if type (node) in (ast.Namespace, ast.DocSection):
            return node.name

        if type (node) in (ast.Signal, ast.VFunction, ast.Property, ast.Field):
            out = "%s%s-%s" % (node.namespace.name, node.parent.name,
                    node.name)

        if type (node) == ast.Function:
            while node:
                if out:
                    out = "%s_%s" % (node.name.lower(), out)
                else:
                    out = node.name

                if hasattr (node, "parent"):
                    node = node.parent
                else:
                    node = None

        elif type (node) in (ast.Class, ast.Enum):
            out = "%s%s" % (node.namespace.name, node.name)

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
            return formatter(node.identifier_prefixes[0])

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
            ('function_call', r'<<symbol_name:alpha>>\(\)'),
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


class AggregatedClass(object):
    def __init__(self, class_node, section_node):
        self.class_node = class_node
        self.__formatter = NameFormatter(language='python')
        self.__section_node = section_node
        self.signals = {}
        self.methods = {}
        self.properties = {}
        self.virtual_functions = {}

    def add_aggregated_node (self, node):
        name = self.__formatter.get_full_node_name (node)
        if type (node) == ast.Signal:
            self.signals[name] = node
        elif type (node) == ast.Function:
            self.methods[name] = node
        elif type (node) == ast.VFunction:
            self.virtual_functions[name] = node
        elif type (node) == ast.Property:
            self.properties[name] = node
        else:
            raise NotImplementedError

    def __sort_symbols (self, nodes):
        sorted_symbols = []
        for symbol in self.__section_node:
            try:
                node = nodes.pop (symbol.text)
                sorted_symbols.append (node)
            except KeyError:
                continue
        return sorted_symbols

    def sort (self):
        self.methods = self.__sort_symbols (self.methods)
        self.signals = self.__sort_symbols (self.signals)
        self.properties = self.__sort_symbols (self.properties)
        self.virtual_functions = self.__sort_symbols (self.virtual_functions)


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

    def resolve_symbol(self, symbol):
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


class PrototypeFormatter(object):
    def __init__ (self, symbol_resolver, language='C'):
        self.__name_formatter = NameFormatter (language=language)
        self.__symbol_resolver = symbol_resolver
        if language == 'C':
            self.make_prototype = self.__make_c_prototype

    def __make_c_prototype (self, node):
        out = ""
        out += "%s " % node.retval.type.ctype
        out += "%s " % self.__name_formatter.get_full_node_name (node)
        out += "("
        for param in node.parameters:
            if out [-1] != "(":
                out += ", "
            out += "%s %s" % (param.type.ctype, param.argname)
        out += ")"
        return out


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
        return "%s#%s" % (self.__pagename, self.__symbol)

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
                    link = ExternalLink (split_line[1], dir_, remote_prefix,
                            split_line[3])
                    symbol_map[split_line[1]] = link

        return symbol_map

    def get_link (self, node):
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
                    return None

        try:
            link = package_links[gtk_doc_identifier]
        except KeyError:
            return None

        return link

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
        self.__prototype_formatter = PrototypeFormatter(self.__symbol_resolver, language='C')

        # Used to aggregate the class with its members
        self.__current_class = None
        self.__aggregated_classes = []

        # Used to warn subclasses a method isn't implemented
        self.__not_implemented_methods = {}

        # Used to avoid parsing code as doc
        self.__processing_code = False

        # Used to create the index file if required
        self.__created_pages = []
 
    def format (self, output):
        self.__walk_node(output, self.__transformer.namespace, [])
        self.__transformer.namespace.walk(lambda node, chain:
                self.__walk_node(output, node, chain))
        if self.__do_class_aggregation:
            self.__aggregate_classes (output)

    def __format_section (self, name, output, elements):
        if not elements:
            return ""

        out = ""
        out += self._format_section (name)

        for elem in elements:
            with open (self.__make_file_name (elem), 'r') as f:
                out += f.read()

        return out

    def __aggregate_classes (self, output):
        for klass in self.__aggregated_classes:
            klass.sort()
            filename = self.__make_file_name (klass.class_node)
            with open (filename, 'a') as f:
                out = ""
                out += self.__format_section ('Properties', output,
                        klass.properties)
                out += self.__format_section ('Methods', output, klass.methods)
                out += self.__format_section ('Signals', output, klass.signals)
                out += self.__format_section ('Virtual Functions', output,
                        klass.virtual_functions)
                f.write (out)

    def format_index (self, output):
        out = ""

        out += self._start_index (self.__transformer.namespace.name)

        filenames = [os.path.splitext(os.path.basename (filename))[0] for
                filename in self.__created_pages]

        out += self._format_index (filenames, self.__sections)

        out += self._end_index ()

        extension = self._get_extension ()
        filename = os.path.join (output, "index.%s" % extension)
        if out:
            with open (filename, 'w') as f:
                f.write (out)

    def __create_handlers (self):
        return {
                ast.Function: self.__handle_function,
                ast.Class: self.__handle_class,
                ast.Signal: self.__handle_signal,
                ast.VFunction: self.__handle_virtual_function,
                ast.DocSection: self.__handle_doc_section,
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

    def __get_link (self, node):
        link = None
        if node.namespace == self.__transformer.namespace:
            if self.__do_class_aggregation and type (node.parent) == ast.Class:
                pagename = self.__make_file_name (node.parent)
            else:
                pagename = self.__make_file_name (node)

            if pagename:
                pagename = os.path.abspath (pagename)
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

    def __get_class_symbols (self, root, node):
        formatter = NameFormatter (language='python')
        node_name = formatter.get_full_node_name (node)
        return_next = False
        for element in root:
            if return_next:
                return element

            if element.text == node_name:
                return_next = True
                continue

            res = self.__get_class_symbols (element, node)
            if res is not None:
                return res
        return None

    def __do_aggregation (self, node):
        if type(node) == ast.Namespace:
            return False

        if type (node) == ast.Class:
            symbol = self.__get_class_symbols (self.__sections, node)
            self.__current_class = AggregatedClass (node, symbol)
            self.__aggregated_classes.append (self.__current_class)
            return False
        elif self.__current_class and node.parent is self.__current_class.class_node:
            self.__current_class.add_aggregated_node (node)
            return True
        else:
            self.__current_class = None
            return False

    def __make_file_name (self, node):
        extension = self._get_extension ()
        name = self.__name_formatter.get_full_node_name (node)
        if not name:
            return ""
        return os.path.join (self.__output, "%s.%s" % (name, extension))

    def __walk_node(self, output, node, chain):
        filename = self.__make_file_name (node)

        try:
            handler = self.__handlers[type (node)]
        except KeyError:
            return True

        with open (filename, 'w') as f:
            out = ""
            out += self._start_page ()
            out += handler (node)
            out += self._end_page ()
            f.write (out)

        if not self.__do_aggregation (node):
            self.__created_pages.append (filename)

        return True

    def __format_doc_string (self, node, docstring):
        if not docstring:
            return ""

        out = ""
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
        out += self._start_doc ()
        out += self.__format_doc_string (node, node.doc)
        out += self._end_doc ()
        return out

    def __format_short_description (self, node):
        if not node.short_description:
            return ""

        out = ""
        out += self._start_short_description ()
        out += self.__format_doc_string (node, node.short_description)
        out += self._end_short_description ()
        return out

    def __handle_parameter (self, node):
        out = ""
        out += self._start_parameter (node.argname)

        logging.debug ("handling parameter %s" % node.argname)
        out += self.__format_doc (node)

        out += self._end_parameter ()

        return out

    def __make_prototypes_for_class (self, node):
        prototypes = []
        for method in node.methods:
            prototypes.append (self.__prototype_formatter.make_prototype
                    (method))
        for method in node.constructors:
            prototypes.append (self.__prototype_formatter.make_prototype
                    (method))

    def __handle_class (self, node):
        out = ""
        prototypes = self.__make_prototypes_for_class (node)
        out += self._start_class (self.__name_formatter.get_full_node_name
                (node), prototypes)

        out += self.__format_short_description (node)
        logging.debug ("handling class %s" % self.__name_formatter.get_full_node_name (node))
        out += self.__format_doc (node)

        out += self._end_class ()

        return out

    def __handle_parameters (self, node):
        out = ""
        if node.all_parameters:
            out += self._start_parameters ()

            for param in node.all_parameters:
                out += self.__handle_parameter (param)

            out += self._end_parameters ()

        return out

    def __handle_signal (self, node):
        out = ""
        out += self._start_signal (self.__name_formatter.get_full_node_name (node))

        out += self.__handle_parameters (node)

        logging.debug ("handling signal %s" % self.__name_formatter.get_full_node_name (node))
        out += self.__format_doc (node)

        out += self._end_signal ()

        return out

    def __handle_function (self, node):
        out = ""
        param_names = []

        for param in node.all_parameters:
            param_names.append (param.argname)

        out += self._start_function (self.__name_formatter.get_full_node_name (node), param_names)

        out += self.__handle_parameters (node)

        logging.debug ("handling function %s" % self.__name_formatter.get_full_node_name (node))
        out += self.__format_doc (node)

        out += self._end_function ()
        return out

    def __handle_virtual_function (self, node):
        out = ""

        out += self._start_virtual_function (self.__name_formatter.get_full_node_name (node))

        out += self.__handle_parameters (node)

        logging.debug ("handling virtual function %s" % self.__name_formatter.get_full_node_name (node))
        out += self.__format_doc (node)

        out += self._end_virtual_function ()

        return out

    def __handle_doc_section (self, node):
        out = ""

        out += self._start_doc_section (node.name)

        logging.debug ("handling doc section %s" % node.name)
        out += self.__format_doc (node)

        out += self._end_doc_section ()

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

    def _start_index (self, namespace_name):
        self.__warn_not_implemented (self._start_index)
        return ""

    def _end_index (self):
        self.__warn_not_implemented (self._end_index)
        return ""

    def _start_doc (self):
        """
        Notifies the subclass that the symbol's documentation
        is going to be parsed
        """
        self.__warn_not_implemented (self._start_doc)
        return ""

    def _end_doc (self):
        """
        Notifies the subclass that the symbol's documentation
        has been parsed, it is safe to assume no _render_
        virtual methods will be called until the next call
        to _start_doc or _start_short_description
        """
        self.__warn_not_implemented (self._end_doc)
        return ""

    def _start_short_description (self):
        """
        Notifies the subclass that the symbol's short description
        is going to be parsed
        """
        self.__warn_not_implemented (self._start_short_description)
        return ""

    def _end_short_description (self):
        """
        Notifies the subclass that the symbol's short description
        has been parsed, it is safe to assume no _render_
        virtual methods will be called until the next call
        to _start_doc or _start_short_description
        """
        self.__warn_not_implemented (self._end_short_description)
        return ""

    def _start_page (self):
        """
        Notifies the subclass that an empty page has been
        started.
        """
        self.__warn_not_implemented (self._start_page)
        return ""

    def _end_page (self):
        """
        Notifies the subclass that the current page is
        finished
        """
        self.__warn_not_implemented (self._end_page)
        return ""

    def _start_doc_section (self, section_name):
        """
        Notifies the subclass that a standalone doc section
        is being parsed
        """
        self.__warn_not_implemented (self._start_doc_section)
        return ""

    def _end_doc_section (self):
        """
        Notifies the subclass that a standalone doc section
        is done being parsed
        """
        self.__warn_not_implemented (self._end_doc_section)
        return ""

    def _start_class (self, class_name, prototypes):
        """
        Notifies the subclass that a class is being
        parsed
        @prototypes: Prototypes of the methods of the class as a list of strings
        """
        self.__warn_not_implemented (self._start_class)
        return ""

    def _end_class (self):
        """
        Notifies the subclass that a class is done being parsed
        """
        self.__warn_not_implemented (self._end_class)
        return ""

    def _start_function (self, function_name, params):
        """
        Notifies the subclass that a function is being parsed
        """
        self.__warn_not_implemented (self._start_function)
        return ""

    def _end_function (self):
        """
        Notifies the subclass that a function is done being parsed
        """
        self.__warn_not_implemented (self._end_function)
        return ""

    def _start_virtual_function (self, function_name):
        """
        Notifies the subclass that a virtual function is being parsed
        """
        self.__warn_not_implemented (self._start_virtual_function)
        return ""

    def _end_virtual_function (self):
        """
        Notifies the subclass that a virtual function is done being parsed
        """
        self.__warn_not_implemented (self._end_virtual_function)
        return ""

    def _start_signal (self, signal_name):
        """
        Notifies the subclass that a signal is being parsed
        """
        self.__warn_not_implemented (self._start_signal)
        return ""

    def _end_signal (self):
        """
        Notifies the subclass that a signal is done being parsed
        """
        self.__warn_not_implemented (self._end_signal)
        return ""

    def _start_parameters (self):
        """
        Notifies the subclass that parameters are being parsed
        """
        self.__warn_not_implemented (self._start_parameters)
        return ""

    def _end_parameters (self):
        """
        Notifies the subclass that parameters are done being parsed
        """
        self.__warn_not_implemented (self._end_parameters)
        return ""

    def _start_parameter (self, param_name):
        """
        Notifies the subclass that a parameter is being parsed
        """
        self.__warn_not_implemented (self._start_parameter)
        return ""

    def _end_parameter (self):
        """
        Notifies the subclass that a parameter is done being parsed
        """
        self.__warn_not_implemented (self._end_parameter)
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
        Called when the parsed markup contains code to render,
        with no specified language
        """
        self.__warn_not_implemented (self._format_code_start)
        return ""

    def _format_code_start_with_language (self, language):
        """
        Called when the parsed markup contains code to render
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

    def _format_section (self, section_name):
        """
        Called when aggregating signals, properties, virtual functions
        and functions to their parent class
        @section_name: the name of the section (Signals, Methods ...)
        """
        self.__warn_not_implemented (self._format_section)
        return ""

    def _format_index (self, filenames, sections):
        """
        Called to render an index
        @filenames: the files that have been produced by the parsing
        @sections: The root of an element tree representing the sections file
        """
        self.__warn_not_implemented (self._format_index)
        return ""
