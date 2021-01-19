import os
from collections import defaultdict
from lxml import etree
import networkx as nx
from hotdoc.core.symbols import QualifiedSymbol
from hotdoc.core.exceptions import BadInclusionException
from hotdoc.extensions.gi.utils import *
from hotdoc.utils.utils import DATADIR
from hotdoc.utils.loggable import warn, Logger


Logger.register_warning_code('missing-gir-include', BadInclusionException,
                             'gi-extension')


'''
Names of boilerplate GObject macros we don't want to expose
'''
SMART_FILTERS = set()


def __generate_smart_filters(id_prefixes, sym_prefixes, node):
    sym_prefix = node.attrib['{%s}symbol-prefix' % NS_MAP['c']]
    SMART_FILTERS.add(('%s_IS_%s' % (sym_prefixes, sym_prefix)).upper())
    SMART_FILTERS.add(('%s_TYPE_%s' % (sym_prefixes, sym_prefix)).upper())
    SMART_FILTERS.add(('%s_%s' % (sym_prefixes, sym_prefix)).upper())
    SMART_FILTERS.add(('%s_%s_CLASS' % (sym_prefixes, sym_prefix)).upper())
    SMART_FILTERS.add(('%s_IS_%s_CLASS' % (sym_prefixes, sym_prefix)).upper())
    SMART_FILTERS.add(('%s_%s_GET_CLASS' % (sym_prefixes, sym_prefix)).upper())
    SMART_FILTERS.add(('%s_%s_GET_IFACE' % (sym_prefixes, sym_prefix)).upper())


__HIERARCHY_GRAPH = nx.DiGraph()


ALL_GI_TYPES = {}
ALL_CALLBACK_TYPES = set()


# Avoid parsing gir files multiple times
__PARSED_GIRS = set()


def __find_gir_file(gir_name, all_girs):
    if gir_name in all_girs:
        return all_girs[gir_name]

    xdg_dirs = os.getenv('XDG_DATA_DIRS') or ''
    xdg_dirs = [p for p in xdg_dirs.split(os.pathsep) if p]
    xdg_dirs.append(DATADIR)
    for dir_ in xdg_dirs:
        gir_file = os.path.join(dir_, 'gir-1.0', gir_name)
        if os.path.exists(gir_file):
            return gir_file

    typelib_path = os.getenv('GI_TYPELIB_PATH') or ''
    typelib_path = [p for p in typelib_path.split(os.pathsep) if p]
    for dir_ in typelib_path:
        gir_file = os.path.join(dir_, gir_name)
        if os.path.exists(gir_file):
            return gir_file

    return None


__TRANSLATED_NAMES = {l: {} for l in OUTPUT_LANGUAGES}


def get_field_c_name_components(node, components):
    parent = node.getparent()
    if parent.tag != core_ns('namespace'):
        get_field_c_name_components(parent, components)
    component = node.attrib.get(c_ns('type'), node.attrib.get('name'))

    if component:
        components.append(component)


def get_field_c_name(node):
    components = []
    get_field_c_name_components(node, components)
    return '.'.join(components)

def __update_hierarchies(cur_ns, node, gi_name):
    parent_name = node.attrib.get('parent')
    if not parent_name:
        # fundamental
        __HIERARCHY_GRAPH.add_node(gi_name)
        return

    if not '.' in parent_name:
        parent_name = '%s.%s' % (cur_ns, parent_name)

    __HIERARCHY_GRAPH.add_edge(parent_name, gi_name)


def __get_parent_link_recurse(gi_name, res):
    parents = list(__HIERARCHY_GRAPH.predecessors(gi_name))
    if parents:
        __get_parent_link_recurse(list(parents)[0], res)
    ctype_name = ALL_GI_TYPES[gi_name]
    qs = QualifiedSymbol(type_tokens=[Link(None, ctype_name, ctype_name)])
    qs.add_extension_attribute ('gi-extension', 'type_desc',
            SymbolTypeDesc([], gi_name, ctype_name, 0))
    res.append(qs)


def get_klass_parents(gi_name):
    '''
    Returns a sorted list of qualified symbols representing
    the parents of the klass-like symbol named gi_name
    '''
    res = []
    parents = list(__HIERARCHY_GRAPH.predecessors(gi_name))
    if not parents:
        return []
    __get_parent_link_recurse(parents[0], res)
    return res


def get_klass_children(gi_name):
    '''
    Returns a dict of qualified symbols representing
    the children of the klass-like symbol named gi_name
    '''
    res = {}
    children = __HIERARCHY_GRAPH.successors(gi_name)
    for gi_name in children:
        ctype_name = ALL_GI_TYPES[gi_name]
        qs = QualifiedSymbol(type_tokens=[Link(None, ctype_name, ctype_name)])
        qs.add_extension_attribute ('gi-extension', 'type_desc',
                SymbolTypeDesc([], gi_name, ctype_name, 0))
        res[ctype_name] = qs
    return res


def cache_nodes(gir_root, all_girs, languages):
    '''
    Identify and store all the gir symbols the symbols we will document
    may link to, or be typed with
    '''
    ns_node = gir_root.find('./{%s}namespace' % NS_MAP['core'])
    id_prefixes = ns_node.attrib['{%s}identifier-prefixes' % NS_MAP['c']]
    sym_prefixes = ns_node.attrib['{%s}symbol-prefixes' % NS_MAP['c']]

    id_key = '{%s}identifier' % NS_MAP['c']
    for node in gir_root.xpath(
            './/*[@c:identifier]',
            namespaces=NS_MAP):
        for language in languages:
            language.make_translations (node.attrib[id_key], node)

    id_type = c_ns('type')
    glib_type = glib_ns('type-name')
    class_tag = core_ns('class')
    callback_tag = core_ns('callback')
    interface_tag = core_ns('interface')
    for node in gir_root.xpath('.//*[not(self::core:type) and not (self::core:array)][@c:type or @glib:type-name]',
            namespaces=NS_MAP):
        try:
            name = node.attrib[id_type]
        except KeyError:
            name = node.attrib[glib_type]
        for language in languages:
            language.make_translations (name, node)
        gi_name = '.'.join(get_gi_name_components(node))
        ALL_GI_TYPES[gi_name] = get_klass_name(node)
        if node.tag in (class_tag, interface_tag):
            __update_hierarchies (ns_node.attrib.get('name'), node, gi_name)
            for language in languages:
                language.make_translations('%s::%s' % (name, name), node)
            __generate_smart_filters(id_prefixes, sym_prefixes, node)
        elif node.tag in (callback_tag,):
            ALL_CALLBACK_TYPES.add(node.attrib[c_ns('type')])

    for field in gir_root.xpath('.//self::core:field', namespaces=NS_MAP):
        unique_name = get_field_c_name(field)
        for language in languages:
            language.make_translations(unique_name, field)

    for node in gir_root.xpath(
            './/core:property',
            namespaces=NS_MAP):
        name = '%s:%s' % (get_klass_name(node.getparent()),
                          node.attrib['name'])
        for language in languages:
            language.make_translations (name, node)

    for node in gir_root.xpath(
            './/glib:signal',
            namespaces=NS_MAP):
        name = '%s::%s' % (get_klass_name(node.getparent()),
                           node.attrib['name'])
        for language in languages:
            language.make_translations (name, node)

    for node in gir_root.xpath(
            './/core:virtual-method',
            namespaces=NS_MAP):
        name = get_symbol_names(node)[0]
        for language in languages:
            language.make_translations (name, node)

    for inc in gir_root.findall('./core:include',
            namespaces = NS_MAP):
        inc_name = inc.attrib["name"]
        inc_version = inc.attrib["version"]
        gir_file = __find_gir_file('%s-%s.gir' % (inc_name, inc_version), all_girs)
        if not gir_file:
            warn('missing-gir-include', "Couldn't find a gir for %s-%s.gir" %
                    (inc_name, inc_version))
            continue

        if gir_file in __PARSED_GIRS:
            continue

        __PARSED_GIRS.add(gir_file)
        inc_gir_root = etree.parse(gir_file).getroot()
        cache_nodes(inc_gir_root, all_girs, languages)


def __type_tokens_from_gitype (cur_ns, ptype_name):
    qs = None

    if ptype_name == 'none':
        return None

    namespaced = '%s.%s' % (cur_ns, ptype_name)
    ptype_name = ALL_GI_TYPES.get(namespaced) or ALL_GI_TYPES.get(ptype_name) or ptype_name

    type_link = Link (None, ptype_name, ptype_name)

    tokens = [type_link]
    tokens += '*'

    return tokens


def __type_tokens_from_cdecl(cdecl):
    indirection = cdecl.count ('*')
    qualified_type = cdecl.strip ('*')
    tokens = []
    for token in qualified_type.split ():
        if token in ["const", "restrict", "volatile"]:
            tokens.append(token + ' ')
        else:
            link = Link(None, token, token)
            tokens.append (link)

    for i in range(indirection):
        tokens.append ('*')

    return tokens


def is_callback_type(c_name):
    return c_name in ALL_CALLBACK_TYPES


def type_description_from_node(gi_node):
    '''
    Parse a typed node, returns a usable description
    '''
    ctype_name, gi_name, array_nesting = unnest_type (gi_node)

    cur_ns = get_namespace(gi_node)

    if ctype_name is not None:
        type_tokens = __type_tokens_from_cdecl (ctype_name)
    else:
        type_tokens = __type_tokens_from_gitype (cur_ns, gi_name)

    namespaced = '%s.%s' % (cur_ns, gi_name)
    if namespaced in ALL_GI_TYPES:
        gi_name = namespaced

    return SymbolTypeDesc(type_tokens, gi_name, ctype_name, array_nesting)


def is_introspectable(name, language):
    '''
    Do not call this before caching the nodes
    '''
    if language.get_fundamental(name):
        return True

    if not language.get_translation(name):
        return False

    return True
