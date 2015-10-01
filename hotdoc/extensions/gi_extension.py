import os
import re

from lxml import etree
import clang.cindex
import pygraphviz as pg

from ..core.symbols import *
from ..core.comment_block import GtkDocParameter, GtkDocCommentBlock
from ..core.doc_tool import doc_tool
from ..core.base_extension import BaseExtension
from ..utils.loggable import Loggable
from .gi_raw_parser import GtkDocRawCommentParser
from .gi_html_formatter import GIHtmlFormatter
from hotdoc.core.links import Link


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

class GIInfo(object):
    def __init__(self, node, parent_name):
        self.node = node
        self.parent_name = re.sub('\.', '', parent_name)

class GIClassInfo(GIInfo):
    def __init__(self, node, parent_name, class_struct_name, is_interface):
        GIInfo.__init__(self, node, parent_name)
        self.class_struct_name = class_struct_name
        self.vmethods = {}
        self.signals = {}
        self.properties = {}
        self.is_interface = is_interface

class GIRParser(object):
    def __init__(self, gir_file):
        self.namespace = None
        self.gir_class_infos = {}
        self.gir_callable_infos = {}
        self.python_names = {}
        self.javascript_names = {}
        self.unintrospectable_symbols = {}
        self.gir_children_map = {}
        self.gir_hierarchies = {}
        self.gir_types = {}
        self.all_infos = {}

        self.callable_nodes = {}

        self.gir_class_map = {}

        self.__parse_gir_file (gir_file)
        self.__create_hierarchies()

    def __create_hierarchies(self):
        for gi_name, klass in self.gir_types.iteritems():
            hierarchy = self.__create_hierarchy (klass)
            self.gir_hierarchies[gi_name] = hierarchy

        hierarchy = []
        for c_name, klass in self.gir_class_infos.iteritems():
            if klass.parent_name != self.namespace:
                continue
            if not klass.node.tag.endswith (('class', 'interface')):
                continue

            gi_name = '%s.%s' % (klass.parent_name, klass.node.attrib['name'])
            klass_name = klass.node.attrib['{%s}type-name' % self.nsmap['glib']]
            cursor = \
                    doc_tool.c_source_scanner.lookup_ast_node(klass_name)
            if cursor:
                type_tokens = doc_tool.c_source_scanner.make_c_style_type_name (cursor.type)
                symbol = QualifiedSymbol(type_tokens, None)
                parents = reversed(self.gir_hierarchies[gi_name])
                for parent in parents:
                    hierarchy.append ((parent, symbol))
                    symbol = parent

        doc_tool.formatter.set_global_hierarchy (hierarchy)

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
            parent_class = self.gir_types[parent_name]
            children = self.gir_children_map.get(parent_name)
            klass_name = klass.attrib['{%s}type-name' % self.nsmap['glib']]

            if not klass_name in children:
                cursor = \
                        doc_tool.c_source_scanner.lookup_ast_node(klass_name)
                if cursor:
                    type_tokens = doc_tool.c_source_scanner.make_c_style_type_name (cursor.type)
                    symbol = QualifiedSymbol (type_tokens, None)
                    children[klass_name] = symbol

            c_name = parent_class.attrib['{%s}type-name' % self.nsmap['glib']]
            cursor = \
                    doc_tool.c_source_scanner.lookup_ast_node(c_name)
            if not cursor:
                break

            type_tokens = doc_tool.c_source_scanner.make_c_style_type_name (cursor.type)
            parent_symbol = QualifiedSymbol (type_tokens, None)
            hierarchy.append (parent_symbol)
            klass = parent_class

        hierarchy.reverse()
        return hierarchy

    def __parse_gir_file (self, gir_file):
        tree = etree.parse (gir_file)
        root = tree.getroot()
        nsmap = {k:v for k,v in root.nsmap.iteritems() if k}
        self.nsmap = nsmap
        for child in root:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}namespace":
                self.__parse_namespace(nsmap, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}include":
                inc_name = child.attrib["name"]
                inc_version = child.attrib["version"]
                gir_file = os.path.join (doc_tool.datadir, 'gir-1.0', '%s-%s.gir' % (inc_name,
                    inc_version))
                self.__parse_gir_file (gir_file)

    def __parse_namespace (self, nsmap, ns):
        ns_name = ns.attrib["name"]
        self.namespace = ns_name
        for child in ns:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}class":
                self.__parse_gir_record(nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}interface":
                self.__parse_gir_record(nsmap, ns_name, child, is_interface=True)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}record":
                self.__parse_gir_record(nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}function":
                self.__parse_gir_function (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}callback":
                self.__parse_gir_callback (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}enumeration":
                self.__parse_gir_enum (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}bitfield":
                self.__parse_gir_enum (nsmap, ns_name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}constant":
                self.__parse_gir_constant (nsmap, ns_name, child)

    def __parse_gir_record (self, nsmap, ns_name, klass, is_interface=False):
        name = '%s.%s' % (ns_name, klass.attrib["name"])
        self.gir_types[name] = klass
        self.gir_children_map[name] = {}
        c_name = klass.attrib.get('{%s}type' % nsmap['c'])
        if not c_name:
            return

        class_struct_name = klass.attrib.get('{http://www.gtk.org/introspection/glib/1.0}type-struct') 

        gi_class_info = GIClassInfo (klass, ns_name, '%s%s' % (ns_name,
            class_struct_name), is_interface)

        if class_struct_name:
            self.gir_class_map['%s%s' % (ns_name, class_struct_name)] = gi_class_info

        self.gir_class_infos[c_name] = gi_class_info
        self.all_infos[c_name] = gi_class_info
        self.python_names[c_name] = name
        self.javascript_names[c_name] = name

        struct_name = c_name + '-struct'
        self.python_names[struct_name] = name
        self.javascript_names[struct_name] = name

        for child in klass:
            if child.tag == "{http://www.gtk.org/introspection/core/1.0}method":
                child_cname = self.__parse_gir_function (nsmap, name, child,
                        is_method=True)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}function":
                child_cname = self.__parse_gir_function (nsmap, name, child)
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}constructor":
                child_cname = self.__parse_gir_function (nsmap, name, child,
                        is_constructor=True)
            elif child.tag == "{http://www.gtk.org/introspection/glib/1.0}signal":
                child_cname = self.__parse_gir_signal (nsmap, c_name, child)
                gi_class_info.signals[child_cname] = child
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}property":
                self.__parse_gir_property (nsmap, c_name, child)
                gi_class_info.properties[child.attrib['name']] = child
            elif child.tag == "{http://www.gtk.org/introspection/core/1.0}virtual-method":
                child_cname = self.__parse_gir_vmethod (nsmap, c_name, child)
                gi_class_info.vmethods[child_cname] = child

    def __parse_gir_callable_common (self, callable_, c_name, python_name,
            js_name, class_name, is_method=False, is_constructor=False):
        introspectable = callable_.attrib.get('introspectable')

        if introspectable == '0':
            self.unintrospectable_symbols[c_name] = True

        self.python_names[c_name] = python_name
        self.javascript_names[c_name] = js_name

        info = GIInfo (callable_, class_name)
        self.gir_callable_infos[c_name] = info
        self.all_infos[c_name] = info

    def __parse_gir_vmethod (self, nsmap, class_name, vmethod):
        name = vmethod.attrib['name']
        c_name = "%s:::%s---%s" % (class_name, name, 'vfunc')
        self.__parse_gir_callable_common (vmethod, c_name, name, name,
                class_name)
        return name

    def __parse_gir_signal (self, nsmap, class_name, signal):
        name = signal.attrib["name"]
        c_name = "%s:::%s---%s" % (class_name, name, 'signal')
        self.__parse_gir_callable_common (signal, c_name, name, name, class_name)
        return name

    def __parse_gir_property (self, nsmap, class_name, prop):
        name = prop.attrib["name"]
        c_name = "%s:::%s---%s" % (class_name, name, 'property')
        self.all_infos[c_name] = GIInfo (prop, class_name)

    def __parse_gir_function (self, nsmap, class_name, function,
            is_method=False, is_constructor=False):
        python_name = '%s.%s' % (class_name, function.attrib['name'])
        js_name = '%s.prototype.%s' % (class_name, function.attrib['name'])
        c_name = function.attrib['{%s}identifier' % nsmap['c']]
        self.__parse_gir_callable_common (function, c_name, python_name,
                js_name, class_name, is_method=is_method,
                is_constructor=is_constructor)
        return c_name

    def __parse_gir_callback (self, nsmap, class_name, function):
        name = '%s.%s' % (class_name, function.attrib['name'])
        c_name = function.attrib['{%s}type' % nsmap['c']]
        self.gir_types[name] = function
        self.__parse_gir_callable_common (function, c_name, name, name,
                class_name)
        return c_name

    def __parse_gir_constant (self, nsmap, class_name, constant):
        name = '%s.%s' % (class_name, constant.attrib['name'])
        c_name = constant.attrib['{%s}type' % nsmap['c']]
        self.python_names[c_name] = name
        self.javascript_names[c_name] = name

    def __parse_gir_enum (self, nsmap, class_name, enum):
        name = '%s.%s' % (class_name, enum.attrib['name'])
        self.gir_types[name] = enum
        c_name = enum.attrib['{%s}type' % nsmap['c']]
        self.python_names[c_name] = name
        self.javascript_names[c_name] = name
        for c in enum:
            if c.tag == "{http://www.gtk.org/introspection/core/1.0}member":
                m_name = '%s.%s' % (name, c.attrib["name"].upper())
                c_name = c.attrib['{%s}identifier' % nsmap['c']]
                self.python_names[c_name] = m_name
                self.javascript_names[c_name] = m_name

    def __get_gir_type (self, name):
        namespaced = '%s.%s' % (self.namespace, name)
        klass = self.gir_types.get (namespaced)
        if klass is not None:
            return klass
        return self.gir_types.get (name)

    def qualified_symbol_from_ctype (self, ctype):
        indirection = ctype.count ('*')
        qualified_type = ctype.strip ('*')
        tokens = []
        for token in qualified_type.split ():
            if token in ["const", "restrict", "volatile"]:
                tokens.append(token)
            else:
                link = doc_tool.link_resolver.get_named_link (token) 
                if link:
                    tokens.append (link)
                else:
                    tokens.append (token)

        for i in range(indirection):
            tokens.append ('*')

        qs = QualifiedSymbol (tokens, None)
        return qs

    def type_tokens_from_gitype (self, ptype_name):
        qs = None

        if ptype_name == 'none':
            return None

        gitype = self.__get_gir_type (ptype_name)
        if gitype is not None:
            c_type = gitype.attrib['{http://www.gtk.org/introspection/c/1.0}type']
            ptype_name = c_type

        type_link = doc_tool.link_resolver.get_named_link (ptype_name)

        if type_link:
            tokens = [type_link]
            tokens += '*'
        else:
            tokens = [ptype_name]

        return tokens

class GIExtension(BaseExtension):
    EXTENSION_NAME = "gi-extension"

    def __init__(self, args):
        BaseExtension.__init__(self, args)
        self.gir_file = args.gir_file
        self.languages = [l.lower() for l in args.languages]
        self.language = 'c'
        self.namespace = None
        self.major_version = args.major_version

        # Make sure C always gets formatted first
        if 'c' in self.languages:
            self.languages.remove ('c')
            self.languages.insert (0, 'c')

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

        self.__raw_comment_parser = GtkDocRawCommentParser()
        self._formatters["html"] = GIHtmlFormatter (self, doc_tool)

    @staticmethod
    def add_arguments (parser):
        parser.add_argument ("--gir-file", action="store",
                dest="gir_file", required=True)
        parser.add_argument ("--languages", action="store",
                nargs='*', default=['c'])
        parser.add_argument ("--major-version", action="store",
                dest="major_version", default='')

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
                elif not remote_prefix:
                    break
                elif l.startswith("<ANCHOR"):
                    split_line = l.split('"')
                    filename = split_line[3].split('/', 1)[-1]
                    title = split_line[1].replace('-', '_')

                    if title.endswith (":CAPS"):
                        title = title [:-5]
                    if remote_prefix:
                        href = '%s/%s' % (remote_prefix, filename)
                    else:
                        href = filename

                    prev_link = doc_tool.link_resolver.get_named_link (title)

                    if not prev_link:
                        link = Link (href, title, title)
                        doc_tool.link_resolver.add_link (link)
                    elif not prev_link.ref:
                        prev_link.ref = href

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

    def __remove_vmethods (self, symbol):
        gir_class_info = self.gir_parser.gir_class_map.get(symbol._make_name())
        if not gir_class_info:
            return

        members = []
        for m in symbol.members:
            if not m.member_name in gir_class_info.vmethods:
                members.append(m)
        symbol.members = members

    def __add_annotations (self, symbol):
        if self.language == 'c':
            annotations = self.get_annotations (symbol)
            extra_content = doc_tool.formatter._format_annotations (annotations)
        else:
            extra_content = ''
        symbol.extension_contents['Annotations'] = extra_content

    def __formatting_symbol(self, symbol):
        if type(symbol) in [ReturnValueSymbol, ParameterSymbol]:
            self.__add_annotations (symbol)

        c_name = symbol._make_name ()

        if type (symbol) == StructSymbol:
            self.__remove_vmethods(symbol)

        # We discard symbols at formatting time because they might be exposed
        # in other languages
        if self.language != 'c':
            if c_name in self.gir_parser.unintrospectable_symbols:
                return False
            if type (symbol) in [FunctionMacroSymbol, ExportedVariableSymbol]:
                return False

        return True

    def setup_language (self, language):
        self.language = language

        if language == 'c':
            return

        if language == 'python':
            for c_name, python_name in self.gir_parser.python_names.iteritems():
                l = doc_tool.link_resolver.get_named_link (c_name)
                if l:
                    l.title = python_name

        elif language == 'javascript':
            for c_name, js_name in self.gir_parser.javascript_names.iteritems():
                l = doc_tool.link_resolver.get_named_link (c_name)
                if l:
                    l.title = js_name

    def __fill_index_columns(self, columns):
        columns.append ('Since')

    def __fill_index_row (self, symbol, row):
        info = self.gir_parser.all_infos.get (symbol.link.id_)
        if info:
            link = doc_tool.link_resolver.get_named_link (info.parent_name)
            if link:
                row[2] = link
            if type (info) == GIClassInfo and info.is_interface:
                row[1] = "Interface"

        if not symbol.comment:
            row.append (self.major_version)
            return
        if not 'since' in symbol.comment.tags:
            row.append (self.major_version)
            return
        row.append (symbol.comment.tags.get ('since').value)

    def __unnest_type (self, parameter):
        array_nesting = 0
        array = parameter.find('{http://www.gtk.org/introspection/core/1.0}array')
        while array is not None:
            array_nesting += 1
            parameter = array
            array = parameter.find('{http://www.gtk.org/introspection/core/1.0}array')

        return parameter, array_nesting

    def __type_tokens_from_cdecl (self, cdecl):
        indirection = cdecl.count ('*')
        qualified_type = cdecl.strip ('*')
        tokens = []
        for token in qualified_type.split ():
            if token in ["const", "restrict", "volatile"]:
                tokens.append(token)
            else:
                link = doc_tool.link_resolver.get_named_link (token)
                if link:
                    tokens.append (link)
                else:
                    tokens.append (token)

        for i in range(indirection):
            tokens.append ('*')

        return tokens

    def __type_tokens_and_gi_name_from_gi_node (self, gi_node):
        type_, array_nesting = self.__unnest_type (gi_node)

        varargs = type_.find('{http://www.gtk.org/introspection/core/1.0}varargs')
        if varargs is not None:
            ctype_name = '...'
            ptype_name = 'valist'
        else:
            ptype_ = type_.find('{http://www.gtk.org/introspection/core/1.0}type')
            ctype_name = ptype_.attrib.get('{http://www.gtk.org/introspection/c/1.0}type')
            ptype_name = ptype_.attrib.get('name')

        if ctype_name is not None:
            type_tokens = self.__type_tokens_from_cdecl (ctype_name)
        elif ptype_name is not None:
            type_tokens = self.gir_parser.type_tokens_from_gitype (ptype_name)
        else:
            type_tokens = []

        namespaced = '%s.%s' % (self.gir_parser.namespace, ptype_name)
        if namespaced in self.gir_parser.gir_types:
            ptype_name = namespaced
        return type_tokens, ptype_name

    def __create_parameter_symbol (self, gi_parameter, comment):
        param_name = gi_parameter.attrib['name']
        if comment:
            param_comment = comment.params.get (param_name)
        else:
            param_comment = None

        type_tokens, gi_name = self.__type_tokens_and_gi_name_from_gi_node (gi_parameter)

        res = ParameterSymbol (param_name, type_tokens, param_comment)
        res.add_extension_attribute ('gi-extension', 'gi_name', gi_name)

        direction = gi_parameter.attrib.get('direction')
        if direction is None:
            direction = 'in'
        res.add_extension_attribute ('gi-extension', 'direction', direction)

        return res, direction

    def __create_return_value_symbol (self, gi_retval, comment):
        if comment:
            return_comment = comment.tags.get ('returns')
        else:
            return_comment = None

        type_tokens, gi_name = self.__type_tokens_and_gi_name_from_gi_node(gi_retval)

        res = ReturnValueSymbol (type_tokens, return_comment)
        res.add_extension_attribute ('gi-extension', 'gi_name', gi_name)

        return res

    def __create_parameters_and_retval (self, node, comment):
        gi_parameters = node.find('{http://www.gtk.org/introspection/core/1.0}parameters')

        if gi_parameters is None:
            instance_param = None
            gi_parameters = []
        else:
            instance_param = \
            gi_parameters.find('{http://www.gtk.org/introspection/core/1.0}instance-parameter')
            gi_parameters = gi_parameters.findall('{http://www.gtk.org/introspection/core/1.0}parameter')

        parameters = []

        if instance_param is not None:
            param, direction = self.__create_parameter_symbol (instance_param,
                    comment)
            parameters.append (param)

        out_parameters = []
        for gi_parameter in gi_parameters:
            param, direction = self.__create_parameter_symbol (gi_parameter,
                    comment)
            parameters.append (param)
            if direction != 'in':
                out_parameters.append (param)

        retval = node.find('{http://www.gtk.org/introspection/core/1.0}return-value')
        retval = self.__create_return_value_symbol (retval, comment)
        retval.add_extension_attribute ('gi-extension', 'out_parameters',
                out_parameters)

        return (parameters, retval)

    def __sort_parameters (self, symbol, retval, parameters):
        in_parameters = []
        out_parameters = []

        for i, param in enumerate (parameters):
            if symbol.is_method and i == 0:
                continue

            direction = param.get_extension_attribute ('gi-extension', 'direction')

            if direction == 'in' or direction == 'inout':
                in_parameters.append (param)
            if direction == 'out' or direction == 'inout':
                out_parameters.append (param)

        symbol.add_extension_attribute ('gi-extension',
                'parameters', in_parameters)
        symbol.add_extension_attribute ('gi-extension',
                'out_parameters', out_parameters)

        retval.add_extension_attribute('gi-extension', 'out_parameters',
                out_parameters)

    def __create_signal_symbol (self, node, comment, object_name, name):
        parameters, retval = self.__create_parameters_and_retval (node, comment)
        res = SignalSymbol (object_name, parameters, retval, comment, name, None)

        flags = []

        when = node.attrib.get('when')
        if when == "first":
            flags.append (RunFirstFlag())
        elif when == "last":
            flags.append (RunLastFlag())
        elif when == "cleanup":
            flags.append (RunCleanupFlag())

        no_hooks = node.attrib.get('no-hooks')
        if no_hooks == '1':
            flags.append (NoHooksFlag())

        extra_content = doc_tool.formatter._format_flags (flags)
        res.extension_contents['Flags'] = extra_content

        self.__sort_parameters (res, retval, parameters)

        return res

    def __create_property_symbol (self, node, comment, object_name, name):
        type_tokens, gi_name = self.__type_tokens_and_gi_name_from_gi_node(node)
        type_ = QualifiedSymbol (type_tokens, None)
        type_.add_extension_attribute ('gi-extension', 'gi_name', gi_name)

        flags = []
        writable = node.attrib.get('writable')
        construct = node.attrib.get('construct')
        construct_only = node.attrib.get('construct-only')

        flags.append (ReadableFlag())
        if writable == '1':
            flags.append (WritableFlag())
        if construct_only == '1':
            flags.append (ConstructOnlyFlag())
        elif construct == '1':
            flags.append (ConstructFlag())

        res = PropertySymbol (type_, object_name, comment, name)

        extra_content = doc_tool.formatter._format_flags (flags)
        res.extension_contents['Flags'] = extra_content

        return res

    def __create_vfunc_symbol (self, node, comment, object_name, name):
        parameters, retval = self.__create_parameters_and_retval (node, comment)
        symbol = VFunctionSymbol (object_name, parameters, retval, comment, name,
                None)

        self.__sort_parameters (symbol, retval, parameters)

        return symbol

    def __create_class_symbol (self, symbol, gi_name):
        class_comment = doc_tool.comments.get ('SECTION:%s' %
                symbol.name.lower())
        hierarchy = self.gir_parser.gir_hierarchies.get (gi_name)
        children = self.gir_parser.gir_children_map.get (gi_name)
        class_symbol = ClassSymbol (hierarchy, children, class_comment, symbol.name, None)
        return class_symbol

    def __update_function (self, func):
        gi_info = self.gir_parser.gir_callable_infos.get(func.link.id_)

        if not gi_info:
            return

        func.is_method = gi_info.node.tag.endswith ('method')

        gi_params, retval = self.__create_parameters_and_retval (gi_info.node,
                func.comment)

        func_parameters = func.parameters

        if 'throws' in gi_info.node.attrib:
            func_parameters = func_parameters[:-1]
            func.throws = True

        for i, param in enumerate (func_parameters):
            gi_param = gi_params[i]
            gi_name = gi_param.get_extension_attribute ('gi-extension',
                    'gi_name')
            param.add_extension_attribute ('gi-extension', 'gi_name', gi_name)
            direction = gi_param.get_extension_attribute ('gi-extension',
                    'direction')
            param.add_extension_attribute('gi-extension', 'direction',
                    direction)

        gi_name = retval.get_extension_attribute ('gi-extension',
                'gi_name')
        func.return_value.add_extension_attribute ('gi-extension', 'gi_name',
                gi_name)

        self.__sort_parameters (func, func.return_value, func_parameters)

    def __update_struct (self, symbol):
        split = symbol.name.split(self.gir_parser.namespace)
        if len (split) < 2:
            return []

        gi_name = '%s.%s' % (self.gir_parser.namespace, split[1])
        if not symbol.name in self.gir_parser.gir_class_infos:
            return []

        gi_class_info = self.gir_parser.gir_class_infos[symbol.name]

        symbols = []
        gir_node = gi_class_info.node

        class_symbol = self.__create_class_symbol (symbol, gi_name)

        symbols.append (class_symbol)

        klass_name = gir_node.attrib.get('{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0')

        if klass_name:
            for signal_name, signal_node in gi_class_info.signals.iteritems():
                block_name = '%s::%s' % (klass_name, signal_name)
                comment = doc_tool.comments.get(block_name)
                sym = self.__create_signal_symbol (signal_node, comment,
                        klass_name, signal_name)
                symbols.append (sym)

            for prop_name, prop_node in gi_class_info.properties.iteritems():
                block_name = '%s:%s' % (klass_name, prop_name)
                comment = doc_tool.comments.get(block_name)
                sym = self.__create_property_symbol (prop_node, comment,
                        klass_name, prop_name)
                symbols.append (sym)

        class_struct_name = gi_class_info.class_struct_name
        if class_struct_name:
            for vfunc_name, vfunc_node in gi_class_info.vmethods.iteritems():
                parent_comment = doc_tool.comments.get (class_struct_name)
                comment = None
                if parent_comment:
                    comment = parent_comment.params.get (vfunc_node.attrib['name'])
                if not comment:
                    continue

                block = GtkDocCommentBlock(vfunc_node.attrib['name'], '', 0,
                        [], [], comment.description, [])
                sym = self.__create_vfunc_symbol (vfunc_node, block,
                        klass_name, vfunc_name)
                symbols.append (sym)

        return symbols

    def __adding_symbol (self, symbol):
        res = []

        if isinstance (symbol, FunctionSymbol):
            self.__update_function (symbol)

        elif type (symbol) == StructSymbol:
            res = self.__update_struct (symbol)

        return res

    def setup (self):
        self.__gather_gtk_doc_links()
        doc_tool.page_parser.symbol_added_signal.connect (self.__adding_symbol)
        doc_tool.formatter.formatting_symbol_signals[Symbol].connect(self.__formatting_symbol)
        doc_tool.formatter.fill_index_columns_signal.connect(self.__fill_index_columns)
        doc_tool.formatter.fill_index_row_signal.connect(self.__fill_index_row)
        if self.gir_file:
            self.gir_parser = GIRParser (self.gir_file)
