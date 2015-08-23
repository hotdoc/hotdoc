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

# Copy pasted from giscanner/gdumpparser to remove any dependency on gi
G_PARAM_READABLE = 1 << 0
G_PARAM_WRITABLE = 1 << 1
G_PARAM_CONSTRUCT = 1 << 2
G_PARAM_CONSTRUCT_ONLY = 1 << 3

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

    def do_format (self):
        return Symbol.do_format(self)

class GIFlaggedSymbol(GISymbol):
    def _make_name(self):
        return self._symbol.attrib["name"]

    def __init__(self, *args):
        self.flags = []
        GISymbol.__init__(self, *args)

class GIPropertySymbol (GIFlaggedSymbol):
    def _make_unique_id(self):
        parent_name = self._symbol.getparent().attrib['name']
        res = "%s:::%s---%s" % (parent_name, self._symbol.attrib["name"],
                'property')
        return res

    def do_format (self):
        self.flags = []
        flags = int(self._symbol.attrib["flags"])
        if flags & G_PARAM_READABLE:
            self.flags.append (ReadableFlag())
        if flags & G_PARAM_WRITABLE:
            self.flags.append (WritableFlag())
        if flags & G_PARAM_CONSTRUCT_ONLY:
            self.flags.append (ConstructOnlyFlag())
        elif flags & G_PARAM_CONSTRUCT:
            self.flags.append (ConstructFlag())
        type_name = self._symbol.attrib["type"]
        self.type_ = self.make_qualified_symbol(type_name)
        return GIFlaggedSymbol.do_format(self)


class GISignalSymbol (GIFlaggedSymbol, FunctionSymbol):
    def _make_unique_id(self):
        parent_name = self._symbol.getparent().attrib['name']
        return "%s:::%s---%s" % (parent_name, self._symbol.attrib["name"],
                'signal')

    def do_format (self):
        parent_name = self._symbol.getparent().attrib['name']
        rtype_name = self._symbol.attrib["return"]
        self.return_value = self.make_qualified_symbol (rtype_name)
        self.return_value.do_format()
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
        dumped_params = list (self._symbol.findall ('param'))
        for param_name, param_comment in self.comment.params.iteritems():
            if i == 0:
                type_ = self.make_qualified_symbol (parent_name)
            else:
                type_ = self.make_qualified_symbol(
                        dumped_params[i - 1].attrib['type'])
            parameter = self._symbol_factory.make_custom_parameter_symbol\
                    (param_comment, type_.type_tokens, param_name)
            parameter.do_format()
            self.parameters.append(parameter)
            i += 1

        udata_type = self.make_qualified_symbol ("gpointer")
        udata_comment = GtkDocParameter ("user_data", [],
                "user data set when the signal handler was connected.")
        udata_param = self._symbol_factory.make_custom_parameter_symbol\
                (udata_comment, udata_type.type_tokens, 'user_data')
        udata_param.do_format()
        self.parameters.append (udata_param)

        return GIFlaggedSymbol.do_format(self)


class GIClassSymbol (GISymbol, ClassSymbol):
    def symbol_init (self, extra_args):
        xml_node = extra_args['xml_node']
        self.__children_names = extra_args['children']
        self.xml_node = xml_node
        self._register_typed_symbol (GIPropertySymbol, "Properties")
        self._register_typed_symbol (GISignalSymbol, "Signals")

        for prop_node in xml_node.findall('property'):
            parent_name = prop_node.getparent().attrib['name']
            block_name = '%s:%s' % (parent_name, prop_node.attrib['name'])
            comment = doc_tool.comments.get(block_name)
            self.add_symbol (self._symbol_factory.make_custom (prop_node,
                comment, GIPropertySymbol))
        for prop_node in xml_node.findall('signal'):
            parent_name = prop_node.getparent().attrib['name']
            block_name = '%s::%s' % (parent_name, prop_node.attrib['name'])
            comment = doc_tool.comments.get(block_name)
            if not comment: # We do need a comment here
                continue
            self.add_symbol (self._symbol_factory.make_custom (prop_node,
                comment, GISignalSymbol))

    def do_format (self):
        self.hierarchy = []
        self.children = []
        self.__create_hierarchy(self._symbol)
        self.hierarchy.reverse()
        return ClassSymbol.do_format(self)

    def __create_hierarchy (self, symbol):
        for parent in self.xml_node.attrib['parents'].split(','):
            cursor = \
                    doc_tool.source_scanner.lookup_ast_node(parent)
            if not cursor:
                continue
            parent_symbol = self._symbol_factory.make_qualified_symbol (cursor.type, None)
            self.hierarchy.append (parent_symbol)
        for child in self.__children_names:
            cursor = doc_tool.source_scanner.lookup_ast_node(child)
            if not cursor:
                continue
            child_symbol = self._symbol_factory.make_qualified_symbol (cursor.type, None)
            self.children.append (child_symbol)


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
        xml_dump = args.gi_dump
        gir_file = args.gir_file
        self.languages = [l.lower() for l in args.languages]

        # Make sure C always gets formatted first
        if 'c' in self.languages:
            self.languages.remove ('c')
            self.languages.insert (0, 'c')

        self._gi_classes = {}
        root = etree.parse (xml_dump).getroot()

        self.python_names = {}

        self.python_links = {}

        self.unintrospectable_symbols = {}

        self.children_map = {}
        for klass in root.findall("class"):
            self._gi_classes[klass.attrib["name"]] = klass
            self.children_map[klass.attrib["name"]] = []

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

        self.__create_chilren_map(root)
        self.__gather_gtk_doc_links()
        self.__raw_comment_parser = GtkDocRawCommentParser()
        self._formatters["html"] = GIHtmlFormatter (self)

    @staticmethod
    def add_arguments (parser):
        parser.add_argument ("--gi-dump", action="store",
                dest="gi_dump")
        parser.add_argument ("--gir-file", action="store",
                dest="gir_file")
        parser.add_argument ("--languages", action="store",
                nargs='*', default=['c'])

    def __quickscan_gir_file (self, gir_file):
        tree = etree.parse (gir_file)
        root = tree.getroot()
        nsmap = {k:v for k,v in root.nsmap.iteritems() if k}
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
        for child in ns:
            if child.tag in ["{http://www.gtk.org/introspection/core/1.0}class",
                    "{http://www.gtk.org/introspection/core/1.0}record"]:
                self.__quickscan_gir_class(nsmap, ns_name, child)
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

    def __quickscan_gir_class (self, nsmap, ns_name, klass):
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

    def __create_chilren_map (self, root):
        for klass in root.findall ("class"):
            parent = klass.attrib["parents"].split(',')[0]
            children = self.children_map.get(parent)
            if not type(children) == list: # External parents
                continue
            children.append (klass.attrib['name'])

    def get_section_type (self, symbol):
        if type (symbol) != clang.cindex.Cursor:
            return (None, None)

        if not symbol.spelling in self._gi_classes:
            return (None, None)

        extra_args = {'xml_node': self._gi_classes[symbol.spelling],
                      'children': self.children_map[symbol.spelling]}
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
        print "setting up language"
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
