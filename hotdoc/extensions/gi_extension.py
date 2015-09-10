import os
import re

from lxml import etree
import clang.cindex
import pygraphviz as pg

from ..core.symbols import (Symbol, FunctionSymbol, ClassSymbol,
        ParameterSymbol, ReturnValueSymbol, FunctionMacroSymbol, ConstantSymbol,
        ExportedVariableSymbol, StructSymbol)
from ..core.comment_block import GtkDocParameter, GtkDocCommentBlock
from ..core.doc_tool import doc_tool
from ..core.base_extension import BaseExtension
from ..utils.loggable import Loggable
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

class GIFlaggedSymbol(Symbol):
    def _make_name(self):
        return self._symbol.attrib["name"]

    def __init__(self, *args):
        self.flags = []
        Symbol.__init__(self, *args)
        self.ns_name = self._symbol.getparent().getparent().attrib['name']
        self.parent_name = self._symbol.getparent().attrib['{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0']

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
        if self.extension.language == 'c' and \
                '{http://www.gtk.org/introspection/c/1.0}type' in type_.attrib:
            ctype_name = type_.attrib.get('{http://www.gtk.org/introspection/c/1.0}type')
            self.type_ = self.extension.gir_parser.qualified_symbol_from_ctype (ctype_name)
        else:
            type_name = type_.attrib['name']
            self.type_ = self.extension.gir_parser.qualified_symbol_from_gitype(type_name, self.extension.language)

        return GIFlaggedSymbol.do_format(self)

    def get_type_name (self):
        return "Property"

class GISignalSymbol (GIFlaggedSymbol, FunctionSymbol):
    def __init__(self, *args):
        GIFlaggedSymbol.__init__(self, *args)
        FunctionSymbol.__init__(self, *args)

    def _make_unique_id(self):
        parent_name = self._symbol.getparent().attrib['{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0']
        return "%s:::%s---%s" % (parent_name, self._symbol.attrib["name"],
                'signal')

    def do_format (self):
        parent_name = self._symbol.getparent().attrib['{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0']

        self.flags = []
        self.return_value = None
        self.parameters = []

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

        return GIFlaggedSymbol.do_format(self)

    def get_type_name (self):
        return "Signal"

class GIVFunctionSymbol (GIFlaggedSymbol, FunctionSymbol):
    def __init__(self, *args):
        GIFlaggedSymbol.__init__(self, *args)
        FunctionSymbol.__init__(self, *args)

    def _make_unique_id(self):
        parent_name = self._symbol.getparent().attrib['{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0']
        res = "%s:::%s---%s" % (parent_name, self._symbol.attrib["name"],
                'vfunc')
        return res

    def do_format (self):
        self.return_value = None
        self.parameters = []
        ns_name =  self._symbol.getparent().getparent().attrib['name']
        self.gi_parent_name = '%s.%s' % (ns_name, self._symbol.getparent().attrib['name'])
        return GIFlaggedSymbol.do_format(self)

    def get_type_name (self):
        return "Virtual function"

class GIClassSymbol (ClassSymbol, Loggable):
    def __init__(self, extra_args, *args):
        Loggable.__init__(self)
        ClassSymbol.__init__(self, *args)
        self.gir_class_info = extra_args['gir-class-info']
        self.__gi_name = extra_args['gi-name']
        self.__gi_extension = extra_args['gi-extension']
        self._register_typed_symbol (GIPropertySymbol, "Properties")
        self._register_typed_symbol (GISignalSymbol, "Signals")
        self._register_typed_symbol (GIVFunctionSymbol, "Virtual Functions")

    def parse_gir_class_info (self):
        gir_node = self.gir_class_info.node

        klass_name = gir_node.attrib.get('{%s}type-name' %
                'http://www.gtk.org/introspection/glib/1.0')
        class_struct_name = self.gir_class_info.class_struct_name

        if klass_name:
            for signal_name, signal_node in self.gir_class_info.signals.iteritems():
                block_name = '%s::%s' % (klass_name, signal_node.attrib['name'])
                comment = doc_tool.comments.get(block_name)
                if not comment: # We do need a comment here
                    continue
                self.add_symbol (doc_tool.symbol_factory.make_custom (signal_node,
                    comment, GISignalSymbol))
            for prop_name, prop_node in self.gir_class_info.properties.iteritems():
                block_name = '%s:%s' % (klass_name, prop_node.attrib['name'])
                comment = doc_tool.comments.get(block_name)
                if not comment:
                    self.warning ("No comment found for property %s" % block_name)
                prop = doc_tool.symbol_factory.make_custom (prop_node,
                    comment, GIPropertySymbol)
                prop.extension = self.__gi_extension
                self.add_symbol (prop)
        if class_struct_name:
            for vfunc_name, vfunc_node in self.gir_class_info.vmethods.iteritems():
                parent_comment = doc_tool.comments.get (class_struct_name)
                comment = None
                if parent_comment:
                    comment = parent_comment.params.get (vfunc_node.attrib['name'])
                if not comment:
                    continue
                block = GtkDocCommentBlock(vfunc_node.attrib['name'], '', 0,
                        [], [], comment.description, [])
                vfunc = doc_tool.symbol_factory.make_custom (vfunc_node,
                        block, GIVFunctionSymbol)
                self.add_symbol (vfunc)

    def do_format (self):
        self.parse_gir_class_info ()
        self.children = self.__gi_extension.gir_parser.gir_children_map.get(self.__gi_name)
        self.hierarchy = self.__gi_extension.gir_parser.gir_hierarchies.get(self.__gi_name)
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

class GICallableInfo(GIInfo):
    def __init__(self, node, parameters, retval, throws, parent_name,
            is_method, is_contructor):
        GIInfo.__init__(self, node, parent_name)
        self.parameters = parameters
        self.retval = retval
        self.throws = throws
        self.is_method = is_method
        self.is_constructor = is_contructor

class GIParamInfo(object):
    def __init__(self, param_name, type_name, out, ctype_name, array_nesting):
        self.param_name = param_name
        self.type_name = type_name
        self.ctype_name = ctype_name
        self.out = out
        self.array_nesting = array_nesting

class GIReturnValueInfo(object):
    def __init__(self, type_name, ctype_name):
        self.type_name = type_name
        self.ctype_name = ctype_name

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

        self.gir_class_map = {}

        self.__parse_gir_file (gir_file)

        doc_tool.symbols_created_signal.connect (self.__symbols_created)

    def __symbols_created(self):
        for gi_name, klass in self.gir_types.iteritems():
            hierarchy = self.__create_hierarchy (klass)
            self.gir_hierarchies[gi_name] = hierarchy

        hierarchy = []
        for c_name, klass in self.gir_class_infos.iteritems():
            if klass.parent_name != self.namespace:
                continue
            if not klass.node.tag.endswith (('class', 'interface')):
                continue
            if c_name.endswith ('-struct'):
                continue

            gi_name = '%s.%s' % (klass.parent_name, klass.node.attrib['name'])
            klass_name = klass.node.attrib['{%s}type-name' % self.nsmap['glib']]
            cursor = \
                    doc_tool.source_scanner.lookup_ast_node(klass_name)
            if cursor:
                symbol = doc_tool.symbol_factory.make_qualified_symbol(cursor.type, None)
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
        self.gir_class_infos[struct_name] = gi_class_info
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

    def __unnest_type (self, parameter):
        array_nesting = 0
        array = parameter.find('{http://www.gtk.org/introspection/core/1.0}array')
        while array is not None:
            array_nesting += 1
            parameter = array
            array = parameter.find('{http://www.gtk.org/introspection/core/1.0}array')

        return parameter, array_nesting

    def __parse_parameters (self, func):
        parameters = func.find('{http://www.gtk.org/introspection/core/1.0}parameters')
        if parameters is None:
            parameters = []
        else:
            parameters = parameters.findall('{http://www.gtk.org/introspection/core/1.0}parameter')

        gir_params = []

        for parameter in parameters:
            param_name = parameter.attrib['name']
            type_, array_nesting = self.__unnest_type (parameter)

            ptype_ = type_.find('{http://www.gtk.org/introspection/core/1.0}type')

            if ptype_ is None:
                continue

            ptype_name = ptype_.attrib['name']
            out = False
            if 'direction' in parameter.attrib:
                out = parameter.attrib['direction'] == 'out'
            ctype_name = type_.attrib.get('{http://www.gtk.org/introspection/c/1.0}type')
            gir_params.append (GIParamInfo (param_name, ptype_name, out,
                ctype_name, array_nesting))

        return gir_params

    def __parse_retval (self, func):
        retval = func.find('{http://www.gtk.org/introspection/core/1.0}return-value')
        if retval is None:
            return None
        ptype_ = retval.find('{http://www.gtk.org/introspection/core/1.0}type')
        if ptype_ is not None: # FIXME
            ctype_name = ptype_.attrib.get('{http://www.gtk.org/introspection/c/1.0}type')
            return GIReturnValueInfo(ptype_.attrib['name'], ctype_name)
        return None

    def __parse_gir_callable_common (self, callable_, c_name, python_name,
            js_name, class_name, is_method=False, is_constructor=False):
        introspectable = callable_.attrib.get('introspectable')

        if introspectable == '0':
            self.unintrospectable_symbols[c_name] = True

        self.python_names[c_name] = python_name
        self.javascript_names[c_name] = js_name
        parameters = self.__parse_parameters (callable_)
        retval = self.__parse_retval (callable_)
        throws = False

        if 'throws' in callable_.attrib:
            throws = callable_.attrib['throws'] == '1'

        info = GICallableInfo (callable_,
            parameters, retval, throws, class_name, is_method, is_constructor)
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
        return c_name

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

        qs = doc_tool.symbol_factory.make_qualified_symbol (ctype, None,
                tokens)
        return qs

    def qualified_symbol_from_gitype (self, ptype_name, language=None):
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
            if language == 'c' and ptype_name in self.gir_class_infos:
                tokens += '*'
        else:
            tokens = [ptype_name]

        qs = doc_tool.symbol_factory.make_qualified_symbol (ptype_name, None,
                tokens)
        return qs


class GIExtension(BaseExtension):
    EXTENSION_NAME = "gi-extension"

    def __init__(self, args):
        BaseExtension.__init__(self, args)
        self.gir_file = args.gir_file
        self.languages = [l.lower() for l in args.languages]
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

        self.__gather_gtk_doc_links()
        self.__raw_comment_parser = GtkDocRawCommentParser()
        self._formatters["html"] = GIHtmlFormatter (self)

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
                elif l.startswith("<ANCHOR"):
                    split_line = l.split('"')
                    filename = split_line[3].split('/', 1)[-1]
                    title = split_line[1].replace('-', '_')
                    if title.endswith (":CAPS"):
                        title = title [:-5]
                    link = ExternalLink (split_line[1], dir_, remote_prefix,
                            filename, title)
                    doc_tool.link_resolver.add_external_link (link)

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

    def __update_parameters(self, callable_, gi_info):
        if not gi_info:
            return

        retval = None
        ret_info = gi_info.retval
        if ret_info:
            if self.language == 'c' and ret_info.ctype_name:
                qs = self.gir_parser.qualified_symbol_from_ctype (ret_info.ctype_name)
            else:
                qs = self.gir_parser.qualified_symbol_from_gitype(ret_info.type_name)
            if qs:
                if callable_.return_value:
                    comment = callable_.return_value.comment
                else:
                    comment = callable_.comment.tags.get('returns')
                retval = doc_tool.symbol_factory.make_custom_return_value_symbol\
                            (comment, qs.type_tokens)
                callable_.return_value = retval

        parameters = []
        for parameter in gi_info.parameters:
            if self.language == 'c' and parameter.ctype_name:
                qs = self.gir_parser.qualified_symbol_from_ctype (parameter.ctype_name)
            else:
                qs = self.gir_parser.qualified_symbol_from_gitype (parameter.type_name)
            comment = callable_.comment.params.get(parameter.param_name)
            if qs:
                param = doc_tool.symbol_factory.make_custom_parameter_symbol\
                            (comment, qs.type_tokens, parameter.param_name)
                param.out = parameter.out
                param.array_nesting = parameter.array_nesting
                parameters.append (param)

        callable_.parameters = parameters

    def __create_signal_parameters(self, signal, gi_info):
        self.__update_parameters(signal, gi_info)

        if self.language == 'c':
            udata_type = self.gir_parser.qualified_symbol_from_ctype ("gpointer")
        else:
            udata_type = self.gir_parser.qualified_symbol_from_gitype ("gpointer")

        instance_type = self.gir_parser.qualified_symbol_from_gitype(signal.parent_name,
                self.language)
        instance_comment = GtkDocParameter ("object", [],
                "The object that emitted the signal")
        instance_param = doc_tool.symbol_factory.make_custom_parameter_symbol\
                (instance_comment, instance_type.type_tokens, 'object')
        signal.parameters.insert (0, instance_param)

        udata_comment = GtkDocParameter ("user_data", [],
                "user data set when the signal handler was connected.")
        udata_param = doc_tool.symbol_factory.make_custom_parameter_symbol\
                (udata_comment, udata_type.type_tokens, 'user_data')
        signal.parameters.append (udata_param)

    def __create_vmethod_parameters(self, vmethod, gi_info):
        self.__update_parameters(vmethod, gi_info)

        instance_type = self.gir_parser.qualified_symbol_from_gitype(vmethod.parent_name,
                self.language)
        instance_comment = GtkDocParameter ("object", [],
                "An instance of the class implementing the virtual method")
        instance_param = doc_tool.symbol_factory.make_custom_parameter_symbol\
                (instance_comment, instance_type.type_tokens, 'object')
        vmethod.parameters.insert (0, instance_param)

    def __sort_out_parameters (self, callable_):
        callable_.return_value.out_parameters = []
        if callable_.parameters:
            for param in callable_.parameters:
                if hasattr(param, 'out') and param.out:
                    callable_.return_value.out_parameters.append (param)

    def __update_array_nesting (self, callable_):
        if callable_.parameters:
            for param in callable_.parameters:
                if not hasattr(param, 'array_nesting'):
                    param.array_nesting = 0

    def __check_throws(self, callable_, gi_info):
        if not gi_info:
            return

        if gi_info.throws:
            callable_.throws = True

    def __update_callable (self, callable_):
        gi_info = self.gir_parser.gir_callable_infos.get(callable_.link.id_)
        callable_.throws = False
        if gi_info and gi_info.is_method:
            callable_.is_method = True
        if type(callable_) == GISignalSymbol:
            self.__create_signal_parameters(callable_, gi_info)
        elif type(callable_) == GIVFunctionSymbol:
            self.__create_vmethod_parameters(callable_, gi_info)
        elif self.language in ["python", "javascript"]:
            self.__update_parameters(callable_, gi_info)

        if self.language in ["python", "javascript"] and \
                callable_.return_value: # FIXME this could happen
            self.__sort_out_parameters (callable_)

        if self.language in ["python", "javascript"]:
            self.__check_throws (callable_, gi_info)
            self.__update_array_nesting (callable_)

    def __remove_vmethods (self, symbol):
        gir_class_info = self.gir_parser.gir_class_map.get(symbol._make_name())
        if not gir_class_info:
            return

        members = []
        for m in symbol.members:
            if not m.member_name in gir_class_info.vmethods:
                members.append(m)
        symbol.members = members

    def __formatting_symbol(self, symbol):
        c_name = symbol._make_name ()

        if isinstance (symbol, FunctionSymbol):
            self.__update_callable (symbol)

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

    def get_section_type (self, symbol):
        if type (symbol) != clang.cindex.Cursor:
            return (None, None)

        split = symbol.spelling.split(self.gir_parser.namespace)
        if len (split) < 2:
            return (None, None)

        gi_name = '%s.%s' % (self.gir_parser.namespace, split[1])
        if not symbol.spelling in self.gir_parser.gir_class_infos:
            return (None, None)

        gi_class_info = self.gir_parser.gir_class_infos[symbol.spelling]

        extra_args = {'gir-class-info': gi_class_info,
                      'gi-name': gi_name,
                      'gi-extension': self}
        return (GIClassSymbol, extra_args)

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
            if type (info) == GICallableInfo and info.is_constructor:
                row[1] = "Constructor"
            elif type (info) == GIClassInfo and info.is_interface:
                row[1] = "Interface"

        if not symbol.comment:
            row.append (self.major_version)
            return
        if not 'since' in symbol.comment.tags:
            row.append (self.major_version)
            return
        row.append (symbol.comment.tags.get ('since').value)

    def setup (self):
        doc_tool.formatter.formatting_symbol_signals[Symbol].connect(self.__formatting_symbol)
        doc_tool.formatter.fill_index_columns_signal.connect(self.__fill_index_columns)
        doc_tool.formatter.fill_index_row_signal.connect(self.__fill_index_row)
        if self.gir_file:
            self.gir_parser = GIRParser (self.gir_file)
