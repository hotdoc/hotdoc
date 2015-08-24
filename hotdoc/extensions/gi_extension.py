import os

from lxml import etree
import clang.cindex

from ..core.symbols import (Symbol, FunctionSymbol, ClassSymbol,
        ParameterSymbol, ReturnValueSymbol, FunctionMacroSymbol, ConstantSymbol)
from ..core.comment_block import GtkDocParameter
from ..core.doc_tool import doc_tool
from ..core.base_extension import BaseExtension
from .gi_raw_parser import GtkDocRawCommentParser
from .gi_html_formatter import GIHtmlFormatter
from hotdoc.core.links import Link, ExternalLink

class Annotation (object):
    def __init__(self, nick, help_text, value=None):
        self.nick = nick
        self.help_text = help_text
        self.value = value

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


class NoHooksFlag (Flag):
    def __init__(self):
        Flag.__init__(self, "No Hooks",
"https://developer.gnome.org/gobject/unstable/gobject-Signals.html#G-SIGNAL-NO-HOOKS:CAPS")


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


class GISymbol(Symbol):
    def make_qualified_symbol (self, type_name):
        type_link = doc_tool.link_resolver.get_named_link (type_name)
        if type_link:
            tokens = [type_link]
        else:
            tokens = [type_name]

        utype = doc_tool.source_scanner.lookup_underlying_type(type_name)
        if utype == clang.cindex.CursorKind.STRUCT_DECL:
            tokens.append('*')

        return self._symbol_factory.make_qualified_symbol (type_name, None, tokens)

    def workaround_stupid_gir (self, ns_name, type_name):
        namespaced = '%s%s' % (self.ns_name, type_name)
        l = doc_tool.link_resolver.get_named_link (namespaced)
        if l:
            type_ = self.make_qualified_symbol (namespaced)
        else:
            # More stupidity
            if type_name == 'utf8':
                type_name = 'gchararray'
            type_ = self.make_qualified_symbol (type_name)
        return type_


    def do_format (self):
        return Symbol.do_format(self)

class GIFlaggedSymbol(GISymbol):
    def _make_name(self):
        return self._symbol.attrib["name"]

    def __init__(self, *args):
        self.flags = []
        GISymbol.__init__(self, *args)
        self.ns_name = self._symbol.getparent().getparent().attrib['name']

class GIPropertySymbol (GIFlaggedSymbol):
    def _make_unique_id(self):
        parent_name = self._symbol.getparent().attrib['{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0']
        res = "%s:::%s---%s" % (parent_name, self._symbol.attrib["name"],
                'property')
        return res

    def do_format (self):
        self.flags = []
        writable = self._symbol.attrib.get('writable')
        construct = self._symbol.attrib.get('construct')
        construct_only = self._symbol.attrib.get('construct-only')

        self.flags.append (ReadableFlag())
        if writable == '1':
            self.flags.append (WritableFlag())
        if construct_only == '1':
            self.flags.append (ConstructOnlyFlag())
        elif construct == '1':
            self.flags.append (ConstructFlag())
        type_ = self._symbol.find ('{http://www.gtk.org/introspection/core/1.0}type')
        type_name = type_.attrib['name']

        self.type_ = self.workaround_stupid_gir (self.ns_name, type_name)

        return GIFlaggedSymbol.do_format(self)


class GISignalSymbol (GIFlaggedSymbol, FunctionSymbol):
    def _make_unique_id(self):
        parent_name = self._symbol.getparent().attrib['{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0']
        return "%s:::%s---%s" % (parent_name, self._symbol.attrib["name"],
                'signal')

    def do_format (self):
        parent_name = self._symbol.getparent().attrib['{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0']
        retval = self._symbol.find('{http://www.gtk.org/introspection/core/1.0}return-value')
        rtype_ = retval.find('{http://www.gtk.org/introspection/core/1.0}type')
        rtype_name = rtype_.attrib["name"]
        self.return_value = self.workaround_stupid_gir (self.ns_name, rtype_name)
        self.parameters = []

        self.flags = []
        when = self._symbol.attrib.get('when')
        if when == "first":
            self.flags.append (RunFirstFlag())
        elif when == "last":
            self.flags.append (RunLastFlag())
        elif when == "cleanup":
            self.flags.append (CleanupFlag())

        no_hooks = self._symbol.attrib.get('no-hooks')
        if no_hooks == '1':
            self.flags.append (NoHooksFlag())

        i = 0
        parameters = self._symbol.find('{http://www.gtk.org/introspection/core/1.0}parameters')

        if parameters is None:
            parameters = []
        else:
            parameters = parameters.findall ('{http://www.gtk.org/introspection/core/1.0}parameter')

        for param_name, param_comment in self.comment.params.iteritems():
            if i == 0:
                type_ = self.make_qualified_symbol (parent_name)
            else:
                ptype_ = parameters[i - 1].find('{http://www.gtk.org/introspection/core/1.0}type')
                ptype_name = ptype_.attrib['name']
                type_ = self.workaround_stupid_gir (self.ns_name, ptype_name)
            parameter = self._symbol_factory.make_custom_parameter_symbol\
                    (param_comment, type_.type_tokens, param_name)
            self.parameters.append(parameter)
            i += 1

        udata_type = self.make_qualified_symbol ("gpointer")
        udata_comment = GtkDocParameter ("user_data", [],
                "user data set when the signal handler was connected.")
        udata_param = self._symbol_factory.make_custom_parameter_symbol\
                (udata_comment, udata_type.type_tokens, 'user_data')
        self.parameters.append (udata_param)

        return GIFlaggedSymbol.do_format(self)


class GIClassSymbol (GISymbol, ClassSymbol):
    def symbol_init (self, extra_args):
        gir_class = extra_args['gir_class']
        self.__gi_name = extra_args['gi-name']
        self.__gi_extension = extra_args['gi-extension']
        self.gir_class = gir_class
        self._register_typed_symbol (GIPropertySymbol, "Properties")
        self._register_typed_symbol (GISignalSymbol, "Signals")

        klass_name = gir_class.attrib['{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0']
        for child in gir_class:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}property":
                block_name = '%s:%s' % (klass_name, child.attrib['name'])
                comment = doc_tool.comments.get(block_name)
                self.add_symbol (self._symbol_factory.make_custom (child,
                    comment, GIPropertySymbol))
            elif child.tag == "{http://www.gtk.org/introspection/glib/1.0}signal":
                block_name = '%s::%s' % (klass_name, child.attrib['name'])
                comment = doc_tool.comments.get(block_name)
                if not comment: # We do need a comment here
                    continue
                self.add_symbol (self._symbol_factory.make_custom (child,
                    comment, GISignalSymbol))

    def do_format (self):
        self.children = self.__gi_extension.gir_children_map[self.__gi_name]
        self.hierarchy = self.__gi_extension.gir_hierarchies[self.__gi_name]
        return ClassSymbol.do_format(self)

ALLOW_NONE_HELP = \
"NULL is OK, both for passing and returning"

TRANSFER_NONE_HELP = \
"Don't free data after the code is done"

TRANSFER_FULL_HELP = \
"Free data after the code is done"

TRANSFER_FLOATING_HELP = \
"Alias for transfer none, used for objects with floating refs"

TRANSFER_CONTAINER_HELP = \
"Free data container after the code is done"

CLOSURE_HELP = \
"This parameter is a closure for callbacks, many bindings can pass NULL to %s"

CLOSURE_DATA_HELP = \
"This parameter is a closure for callbacks, many bindings can pass NULL here"

DIRECTION_OUT_HELP = \
"Parameter for returning results"

DIRECTION_INOUT_HELP = \
"Parameter for input and for returning results"

DIRECTION_IN_HELP = \
"Parameter for input. Default is transfer none"

ARRAY_HELP = \
"Parameter points to an array of items"

ELEMENT_TYPE_HELP = \
"Generic and defining element of containers and arrays"

SCOPE_ASYNC_HELP = \
"The callback is valid until first called"

SCOPE_CALL_HELP = \
"The callback is valid only during the call to the method"

NULLABLE_HELP = \
"NULL may be passed to the value"

DEFAULT_HELP = \
"Default parameter value (for in case the shadows-to function has less parameters)"

# VERY DIFFERENT FROM THE PREVIOUS ONE BEWARE :P
OPTIONAL_HELP = \
"NULL may be passed instead of a pointer to a location"

# WTF
TYPE_HELP = \
"Override the parsed C type with given type"

class GIExtension(BaseExtension):
    EXTENSION_NAME = "gi-extension"

    def __init__(self, args):
        BaseExtension.__init__(self, args)
        gir_file = args.gir_file
        self.languages = [l.lower() for l in args.languages]
        self.__namespace = None

        # Make sure C always gets formatted first
        if 'c' in self.languages:
            self.languages.remove ('c')
            self.languages.insert (0, 'c')

        self.python_names = {}

        self.python_links = {}

        self.unintrospectable_symbols = {}

        self._gir_classes =   {}
        self.gir_children_map = {}
        self.gir_hierarchies = {}

        if gir_file:
            self.__quickscan_gir_file (gir_file)

        self.__annotation_factories = \
                {"allow-none": self.__make_allow_none_annotation,
                 "transfer": self.__make_transfer_annotation,
                 "inout": self.__make_inout_annotation,
                 "out": self.__make_out_annotation,
                 "in": self.__make_in_annotation,
                 "array": self.__make_array_annotation,
                 "element-type": self.__make_element_type_annotation,
                 "scope": self.__make_scope_annotation,
                 "closure": self.__make_closure_annotation,
                 "nullable": self.__make_nullable_annotation,
                 "type": self.__make_type_annotation,
                 "optional": self.__make_optional_annotation,
                 "default": self.__make_default_annotation,
                }

        self.__gather_gtk_doc_links()
        self.__raw_comment_parser = GtkDocRawCommentParser()
        self._formatters["html"] = GIHtmlFormatter (self)

    @staticmethod
    def add_arguments (parser):
        parser.add_argument ("--gir-file", action="store",
                dest="gir_file")
        parser.add_argument ("--languages", action="store",
                nargs='*', default=['c'])

    def __quickscan_gir_file (self, gir_file):
        tree = etree.parse (gir_file)
        root = tree.getroot()
        nsmap = {k:v for k,v in root.nsmap.iteritems() if k}
        self.nsmap = nsmap
        for child in root:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}namespace":
                self.__quickscan_namespace(nsmap, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}include":
                inc_name = child.attrib["name"]
                inc_version = child.attrib["version"]
                gir_file = os.path.join (doc_tool.datadir, 'gir-1.0', '%s-%s.gir' % (inc_name,
                    inc_version))
                self.__quickscan_gir_file (gir_file)

    def __quickscan_namespace (self, nsmap, ns):
        ns_name = ns.attrib["name"]
        self.__namespace = ns_name
        for child in ns:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}class":
                self.__quickscan_gir_class(nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}record":
                self.__quickscan_gir_record(nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}function":
                self.__quickscan_gir_method (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}callback":
                self.__quickscan_gir_callback (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}enumeration":
                self.__quickscan_gir_enum (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}bitfield":
                self.__quickscan_gir_enum (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}constant":
                self.__quickscan_gir_constant (nsmap, ns_name, child)

    def __quickscan_gir_record (self, nsmap, ns_name, klass):
        name = '%s.%s' % (ns_name, klass.attrib["name"])
        c_name = klass.attrib.get('{%s}type' % nsmap['c'])
        if not c_name:
            return

        self.python_names[c_name] = name
        for child in klass:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}method":
                self.__quickscan_gir_method (nsmap, name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}function":
                self.__quickscan_gir_method (nsmap, name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}constructor":
                self.__quickscan_gir_method (nsmap, name, child)

    def __quickscan_gir_class (self, nsmap, ns_name, klass):
        name = '%s.%s' % (ns_name, klass.attrib["name"])
        self._gir_classes[name] = klass
        self.gir_children_map[name] = {}
        self.__quickscan_gir_record (nsmap, ns_name, klass)

    def __quickscan_gir_constant (self, nsmap, class_name, constant):
        name = '%s.%s' % (class_name, constant.attrib['name'])
        c_name = constant.attrib['{%s}type' % nsmap['c']]
        self.python_names[c_name] = name

    def __quickscan_gir_enum (self, nsmap, class_name, enum):
        name = '%s.%s' % (class_name, enum.attrib['name'])
        c_name = enum.attrib['{%s}type' % nsmap['c']]
        self.python_names[c_name] = name
        for c in enum:
            if c.tag == "{http://www.gtk.org/introspection/core/1.0}member":
                m_name = '%s.%s' % (name, c.attrib["name"].upper())
                c_name = c.attrib['{%s}identifier' % nsmap['c']]
                self.python_names[c_name] = m_name

    def __quickscan_gir_method (self, nsmap, class_name, method):
        name = '%s.%s' % (class_name, method.attrib['name'])
        c_name = method.attrib['{%s}identifier' % nsmap['c']]
        introspectable = method.attrib.get('introspectable')
        if introspectable == '0':
            self.unintrospectable_symbols[c_name] = True
        self.python_names[c_name] = name

    def __quickscan_gir_callback (self, nsmap, class_name, method):
        name = '%s.%s' % (class_name, method.attrib['name'])
        c_name = method.attrib['{%s}type' % nsmap['c']]
        introspectable = method.attrib.get('introspectable')
        if introspectable == '0':
            self.unintrospectable_symbols[c_name] = True
        self.python_names[c_name] = name

    def __gather_gtk_doc_links (self):
        sgml_dir = os.path.join(doc_tool.datadir, "gtk-doc", "html")
        if not os.path.exists(sgml_dir):
            self.error("no gtk doc to gather links from in %s" % sgml_dir)
            return

        for node in os.listdir(sgml_dir):
            dir_ = os.path.join(sgml_dir, node)
            if os.path.isdir(dir_):
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
                    if title.endswith (":CAPS"):
                        title = title [:-5]
                    link = ExternalLink (split_line[1], dir_, remote_prefix,
                            filename, title)
                    doc_tool.link_resolver.add_external_link (link)

    def __create_hierarchy (self, klass):
        klaass = klass
        hierarchy = []
        while (True):
            parent_name = klass.attrib.get('parent')
            if not parent_name:
                break
            if not '.' in parent_name:
                namespace = klass.getparent().attrib['name']
                parent_name = '%s.%s' % (namespace, parent_name)
            parent_class = self._gir_classes[parent_name]
            children = self.gir_children_map.get(parent_name)
            klass_name = klass.attrib['{%s}type-name' % self.nsmap['glib']]

            if not klass_name in children:
                cursor = \
                        doc_tool.source_scanner.lookup_ast_node(klass_name)
                if cursor:
                    symbol = doc_tool.symbol_factory.make_qualified_symbol (cursor.type, None)
                    children[klass_name] = symbol

            c_name = parent_class.attrib['{%s}type-name' % self.nsmap['glib']]
            cursor = \
                    doc_tool.source_scanner.lookup_ast_node(c_name)
            if not cursor:
                break

            parent_symbol = doc_tool.symbol_factory.make_qualified_symbol (cursor.type, None)
            hierarchy.append (parent_symbol)
            klass = parent_class

        hierarchy.reverse()
        return hierarchy

    def get_section_type (self, symbol):
        if type (symbol) != clang.cindex.Cursor:
            return (None, None)

        split = symbol.spelling.split(self.__namespace)
        if len (split) < 2:
            return (None, None)

        gi_name = '%s.%s' % (self.__namespace, split[1])
        if not gi_name in self._gir_classes:
            return (None, None)

        extra_args = {'gir_class': self._gir_classes[gi_name],
                      'gi-name': gi_name,
                      'gi-extension': self}
        return (GIClassSymbol, extra_args)

    def __make_type_annotation (self, annotation, value):
        if not value:
            return None

        return Annotation("type", TYPE_HELP, value[0])

    def __make_nullable_annotation (self, annotation, value):
        return Annotation("nullable", NULLABLE_HELP)

    def __make_optional_annotation (self, annotation, value):
        return Annotation ("optional", OPTIONAL_HELP)

    def __make_allow_none_annotation(self, annotation, value):
        return Annotation ("allow-none", ALLOW_NONE_HELP)

    def __make_transfer_annotation(self, annotation, value):
        if value[0] == "none":
            return Annotation ("transfer: none", TRANSFER_NONE_HELP)
        elif value[0] == "full":
            return Annotation ("transfer: full", TRANSFER_FULL_HELP)
        elif value[0] == "floating":
            return Annotation ("transfer: floating", TRANSFER_FLOATING_HELP)
        elif value[0] == "container":
            return Annotation ("transfer: container", TRANSFER_CONTAINER_HELP)
        else:
            return None

    def __make_inout_annotation (self, annotation, value):
        return Annotation ("inout", DIRECTION_INOUT_HELP)

    def __make_out_annotation (self, annotation, value):
        return Annotation ("out", DIRECTION_OUT_HELP)

    def __make_in_annotation (self, annotation, value):
        return Annotation ("in", DIRECTION_IN_HELP)

    def __make_element_type_annotation (self, annotation, value):
        annotation_val = None
        if type(value) == list:
            annotation_val = value[0]
        return Annotation ("element-type", ELEMENT_TYPE_HELP, annotation_val)

    def __make_array_annotation (self, annotation, value):
        annotation_val = None
        if type(value) == dict:
            annotation_val = ""
            for name, val in value.iteritems():
                annotation_val += "%s=%s" % (name, val)
        return Annotation ("array", ARRAY_HELP, annotation_val)

    def __make_scope_annotation (self, annotation, value):
        if type (value) != list or not value:
            return None

        if value[0] == "async":
            return Annotation ("scope async", SCOPE_ASYNC_HELP)
        elif value[0] == "call":
            return Annotation ("scope call", SCOPE_CALL_HELP)
        return None

    def __make_closure_annotation (self, annotation, value):
        if type (value) != list or not value:
            return Annotation ("closure", CLOSURE_DATA_HELP)

        return Annotation ("closure", CLOSURE_HELP % value[0])

    def __make_default_annotation (self, annotation, value):
        return Annotation ("default %s" % str (value[0]), DEFAULT_HELP)

    def __create_annotation (self, annotation_name, annotation_value):
        factory = self.__annotation_factories.get(annotation_name)
        if not factory:
            return None
        return factory (annotation_name, annotation_value)

    def get_annotations (self, parameter):
        parameter.out = False

        if not parameter.comment:
            return []

        if not parameter.comment.annotations:
            return []

        annotations = []

        for ann, val in parameter.comment.annotations.iteritems():
            if ann == "skip":
                continue
            annotation = self.__create_annotation (ann, val.argument)
            if not annotation:
                print "This parameter annotation is unknown :[" + ann + "]", val.argument
                continue
            annotations.append (annotation)
            if ann == "out":
                parameter.out = True

        return annotations

    def __formatting_symbol(self, symbol):
        c_name = symbol._make_name ()
        # We discard symbols at formatting time because they might be exposed
        # in other languages
        if self.language != 'c':
            if c_name in self.unintrospectable_symbols:
                return False
            if type (symbol) in [FunctionMacroSymbol, ConstantSymbol]:
                return False

        return True

    def setup_language (self, language):
        for gi_name, klass in self._gir_classes.iteritems():
            hierarchy = self.__create_hierarchy (klass)
            self.gir_hierarchies[gi_name] = hierarchy

        self.language = language
        if language == 'c':
            return

        if language == 'python':
            for c_name, python_name in self.python_names.iteritems():
                l = doc_tool.link_resolver.get_named_link (c_name)
                if l:
                    l.title = python_name

    def setup (self):
        doc_tool.formatter.formatting_symbol_signals[Symbol].connect (self.__formatting_symbol)
