import unittest
import importlib
from lxml import etree
PYTHON_LANG = importlib.import_module('hotdoc.extensions.gi.languages.python')
JAVASCRIPT_LANG = importlib.import_module('hotdoc.extensions.gi.languages.javascript')
CACHE_MODULE = importlib.import_module('hotdoc.extensions.gi.node_cache')
from hotdoc.extensions.gi.utils import core_ns, unnest_type

GIR_TEMPLATE = \
'''
<repository version="1.2"
            xmlns="http://www.gtk.org/introspection/core/1.0"
            xmlns:c="http://www.gtk.org/introspection/c/1.0"
            xmlns:glib="http://www.gtk.org/introspection/glib/1.0">
  <include name="GObject" version="2.0"/>
  <package name="test"/>
  <namespace name="Test"
             version="1.0"
             shared-library="libglib-2.0.so.0,libgobject-2.0.so.0,libtestlib.so"
             c:identifier-prefixes="Test"
             c:symbol-prefixes="test">
  %s
  </namespace>
</repository>
'''

TEST_GREETER_LIST_GREETS = \
'''
<method name="list_greets" c:identifier="test_greeter_list_greets">
  <return-value transfer-ownership="full">
    <array c:type="gchar***">
      <array>
        <type name="utf8"/>
      </array>
    </array>
  </return-value>
</method>
'''

TEST_GREETER_LIST_GREETERS = \
'''
<method name="list_greeters" c:identifier="test_greeter_list_greeters">
  <return-value transfer-ownership="full">
    <type name="GLib.List" c:type="GList*">
      <type name="Greeter"/>
    </type>
  </return-value>
</method>
'''

TEST_GREETER_GREET = \
'''
<method name="greet" c:identifier="test_greeter_greet">
  <return-value transfer-ownership="full">
    <type name="utf8" c:type="gchar*"/>
  </return-value>
</method>
'''

TEST_GREETER_DO_NOTHING = \
'''
<method name="do_nothing" c:identifier="test_greeter_do_nothing">
  <return-value>
    <type name="none" c:type="void"/>
  </return-value>
</method>
'''

TEST_GREETER_GREET_MANY = \
'''
<method name="greet_many" c:identifier="test_greeter_greet_many">
  <parameters>
    <parameter name='...' transfer-ownership="none">
      <varargs/>
    </parameter>
  </parameters>
</method>
'''


# Happens in some signals, I assume it's a gi bug but let's check that
# we don't react too bad
TEST_GREETER_GREET_BROKEN = \
'''
<method name="greet_broken" c:identifier="test_greeter_greet_broken">
  <return-value>
    <type/>
  </return-value>
</method>
'''


# Happens in signals
TEST_GREETER_GREET_GI_OBJECT = \
'''
<method name="greet_gi_object" c:identifier="test_greeter_greet_gi_object">
  <return-value>
    <type name="GObject.Object"/>
  </return-value>
</method>
'''


class TestTypeUnnesting(unittest.TestCase):
    def assertRetvalTypesEqual(self, symbol_string, ctype_name, gi_name, array_nesting):
        test_data = GIR_TEMPLATE % symbol_string
        gir_root = etree.fromstring (test_data)
        retval = gir_root.find('.//%s/%s' %
                (core_ns ('method'), core_ns('return-value')))
        self.assertTupleEqual (unnest_type (retval), (ctype_name, gi_name, array_nesting))

    def test_array_type(self):
        self.assertRetvalTypesEqual(TEST_GREETER_LIST_GREETS, 'gchar***', 'utf8', 2)

    def test_list_type(self):
        self.assertRetvalTypesEqual(TEST_GREETER_LIST_GREETERS, 'GList*', 'Greeter', 1)

    def test_string_type(self):
        self.assertRetvalTypesEqual(TEST_GREETER_GREET, 'gchar*', 'utf8', 0)

    def test_none_type(self):
        self.assertRetvalTypesEqual(TEST_GREETER_DO_NOTHING, 'void', 'none', 0)

    def test_unknown_type(self):
        self.assertRetvalTypesEqual(TEST_GREETER_GREET_BROKEN, None, 'object', 0)

    def test_gi_type(self):
        self.assertRetvalTypesEqual(TEST_GREETER_GREET_GI_OBJECT, None, 'GObject.Object', 0)

    def test_varargs_type(self):
        test_data = GIR_TEMPLATE % TEST_GREETER_GREET_MANY
        gir_root = etree.fromstring (test_data)
        param = gir_root.find('.//%s/%s/%s' %
                (core_ns ('method'), core_ns('parameters'), core_ns('parameter')))
        self.assertTupleEqual (unnest_type (param), ('...', 'valist', 0))

class TestNodeCaching(unittest.TestCase):
    def setUp(self):
        importlib.reload(CACHE_MODULE)

    def test_array_type(self):
        test_data = GIR_TEMPLATE % TEST_GREETER_LIST_GREETS
        gir_root = etree.fromstring (test_data)
        pythonlang = PYTHON_LANG.get_language_classes()[0]()
        javascriptlang = JAVASCRIPT_LANG.get_language_classes()[0]()
        CACHE_MODULE.cache_nodes(gir_root, [], {pythonlang, javascriptlang})
        translated = pythonlang.get_translation('test_greeter_list_greets')
        self.assertEqual (translated, 'Test.list_greets')
        translated = javascriptlang.get_translation('test_greeter_list_greets')
        self.assertEqual (translated, 'Test.prototype.list_greets')
        retval = gir_root.find('.//%s/%s' %
                (core_ns ('method'), core_ns('return-value')))
        type_desc = CACHE_MODULE.type_description_from_node(retval)
        self.assertEqual(type_desc.gi_name, 'utf8')
        self.assertEqual(type_desc.c_name, 'gchar***')
        self.assertEqual(type_desc.nesting_depth, 2)
