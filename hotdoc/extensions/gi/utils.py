import os
from collections import namedtuple
import pathlib

import pkg_resources

from hotdoc.core.links import Link


NS_MAP = {'core': 'http://www.gtk.org/introspection/core/1.0',
          'c': 'http://www.gtk.org/introspection/c/1.0',
          'glib': 'http://www.gtk.org/introspection/glib/1.0'}


if os.name == 'nt':
    DATADIR = os.path.join(os.path.dirname(__file__), '..', 'share')
else:
    DATADIR = "/usr/share"


OUTPUT_LANGUAGES = ['c', 'python', 'javascript']


# Describes the type of Return or Parameter symbols
SymbolTypeDesc = namedtuple('SymbolTypeDesc', [
    'type_tokens', 'gi_name', 'c_name', 'nesting_depth'])


def core_ns(tag):
    return '{http://www.gtk.org/introspection/core/1.0}%s' % tag


def glib_ns(tag):
    return '{http://www.gtk.org/introspection/glib/1.0}%s' % tag


def c_ns(tag):
    return '{http://www.gtk.org/introspection/c/1.0}%s' % tag


def get_gi_name_components(node):
    parent = node.getparent()
    if 'name' in node.attrib:
        components = [node.attrib.get('name')]
    else:
        components = []

    while parent is not None:
        try:
            components.insert(0, parent.attrib['name'])
        except KeyError:
            break
        parent = parent.getparent()
    return components


def get_gi_name (node):
    components = get_gi_name_components(node)
    return '.'.join(components)


def get_klass_name(klass):
    klass_name = klass.attrib.get('{%s}type' % NS_MAP['c'])
    if not klass_name:
        klass_name = klass.attrib.get('{%s}type-name' % NS_MAP['glib'])
    return klass_name


def get_function_name(func):
    return func.attrib.get('{%s}identifier' % NS_MAP['c'])


def get_structure_name(node):
    return node.attrib[c_ns('type')]


def get_symbol_names(node):
    if node.tag in (core_ns('class')):
        _ = get_klass_name (node)
        return _, _, _
    elif node.tag in (core_ns('interface')):
        _ = get_klass_name (node)
        return _, _, _
    elif node.tag in (core_ns('function'), core_ns('method'), core_ns('constructor')):
        _ = get_function_name(node)
        return _, _, _
    elif node.tag == core_ns('virtual-method'):
        klass_node = node.getparent()
        ns = klass_node.getparent()
        klass_structure_node = ns.xpath(
            './*[@glib:is-gtype-struct-for="%s"]' % klass_node.attrib['name'],
            namespaces=NS_MAP)[0]
        parent_name = get_structure_name(klass_structure_node)
        name = node.attrib['name']
        unique_name = '%s::%s' % (parent_name, name)
        return unique_name, name, unique_name
    elif node.tag == core_ns('field'):
        structure_node = node.getparent()
        parent_name = get_structure_name(structure_node)
        name = node.attrib['name']
        unique_name = '%s::%s' % (parent_name, name)
        return unique_name, name, unique_name
    elif node.tag == core_ns('property'):
        parent_name = get_klass_name(node.getparent())
        klass_name = '%s::%s' % (parent_name, parent_name)
        name = node.attrib['name']
        unique_name = '%s:%s' % (parent_name, name)
        return unique_name, name, klass_name
    elif node.tag == glib_ns('signal'):
        parent_name = get_klass_name(node.getparent())
        klass_name = '%s::%s' % (parent_name, parent_name)
        name = node.attrib['name']
        unique_name = '%s::%s' % (parent_name, name)
        return unique_name, name, klass_name
    elif node.tag == core_ns('alias'):
        _ = node.attrib.get(c_ns('type'))
        return _, _, _
    elif node.tag == core_ns('record'):
        _ = get_structure_name(node)
        return _, _, _
    elif node.tag in (core_ns('enumeration'), core_ns('bitfield')):
        _ = node.attrib[c_ns('type')]
        return _, _, _

    return None, None, None


def unnest_type (node):
    array_nesting = 0

    varargs = node.find(core_ns ('varargs'))
    if varargs is not None:
        return '...', 'valist', 0

    type_ = node.find(core_ns('array'))
    if type_ is None:
        type_ = node.find(core_ns('type'))
    ctype_name = type_.attrib.get(c_ns('type'), None)

    while type_.tag == core_ns('array') or type_.attrib.get('name') == 'GLib.List':
        subtype_ = type_.find(core_ns('array'))
        if subtype_ is None:
            subtype_ = type_.find(core_ns('type'))
        type_ = subtype_
        array_nesting += 1

    return ctype_name, type_.attrib.get('name', 'object'), array_nesting


def get_namespace(node):
    parent = node.getparent()
    nstag = '{%s}namespace' % NS_MAP['core']
    while parent is not None and parent.tag != nstag:
        parent = parent.getparent()

    return parent.attrib['name']


def get_array_type(node):
    array = node.find(core_ns('array'))
    if array is None:
        return None

    return array.attrib[c_ns('type')]


def get_return_type_from_callback(node):
    return_node = node.find(core_ns('return-value'))
    array_type = get_array_type(return_node)
    if array_type:
        return array_type

    return return_node.find(core_ns('type')).attrib[c_ns('type')]


def insert_language(ref, language, project):
    if not ref.startswith(project.sanitized_name + '/'):
        return language + '/' + ref

    p = pathlib.Path(ref)
    return str(pathlib.Path(p.parts[0], language, *p.parts[1:]))

def get_field_c_name_components(node, components):
    parent = node.getparent()
    if parent.tag != core_ns('namespace'):
        get_field_c_name_components(parent, components)
    component = node.attrib.get(c_ns('type'), node.attrib.get('name'))

    if component:
        components.append(component)

# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
def get_language_classes():
    """
    Banana banana
    """
    all_classes = {}
    deps_map = {}

    for entry_point in pkg_resources.iter_entry_points(
            group='hotdoc.extensions.gi.languages', name='get_language_classes'):
        try:
            activation_function = entry_point.load()
            classes = activation_function()
        # pylint: disable=broad-except
        except Exception as exc:
            info("Failed to load %s" % entry_point.module_name, exc)
            debug(traceback.format_exc())
            continue

        for klass in classes:
            all_classes[klass.language_name] = klass

    return list(all_classes.values())
