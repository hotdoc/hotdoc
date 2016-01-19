# -*- coding: utf-8 -*-

import cPickle as pickle
import io
import linecache
import os
import shutil
from collections import OrderedDict
from xml.sax.saxutils import unescape

import CommonMark
from hotdoc.core.links import Link
from hotdoc.core.symbols import *
from hotdoc.utils.simple_signals import Signal


class TypedSymbolsList (object):
    def __init__ (self, name):
        self.name = name
        self.symbols = []


def get_children(node, recursive=False):
    if not recursive:
        child = node.first_child
        while (child):
            nxt = child.nxt
            yield child
            child = nxt
    else:
        walker = node.walker()
        nxt = walker.nxt()
        while nxt is not None:
            yield nxt['node']
            nxt = walker.nxt()

def get_label(link, recursive=False):
    return ''.join(c.literal or '' for c in get_children(link, recursive))

def set_label(parser, node, text):
        for c in get_children(node):
            c.unlink()

        new_label = parser.parse(text)

        # We only want Document -> Paragraph -> children
        for c in get_children(new_label.first_child):
            node.append_child(c)

class Page(object):
    def __init__(self, source_file, extension_name):
        name = os.path.splitext(os.path.basename(source_file))[0]
        pagename = '%s.html' % name

        self.symbol_names = []
        self.subpages = OrderedDict({})
        self.link = Link (pagename, name, name) 
        self.title = None
        self.first_header = None
        self.first_paragraph = None
        self.short_description = None
        self.source_file = source_file
        self.output_attrs = None
        self.extension_name = extension_name
        try:
            self.mtime = os.path.getmtime(source_file)
        except OSError:
            self.mtime = -1

        self.is_stale = True
        self.ast = None
        self.headers = {}
        self.reference_map = set()

    def __getstate__(self):
        return {'symbol_names': self.symbol_names,
                'subpages': self.subpages,
                'link': self.link,
                'title': self.title,
                'first_header': self.first_header,
                'first_paragraph': self.first_paragraph,
                'short_description': self.short_description,
                'source_file': self.source_file,
                'reference_map': self.reference_map,
                'output_attrs': None,
                'extension_name': self.extension_name,
                'ast': None,
                'headers': {},
                'is_stale': False, # At pickle time, we can assume non-staleness
                'mtime': self.mtime}

    def resolve_symbols (self, doc_tool):
        self.symbols = []

        self.typed_symbols = {}
        self.typed_symbols[Symbol] = TypedSymbolsList ('FIXME symbols')
        self.typed_symbols[FunctionSymbol] = TypedSymbolsList ("Functions")
        self.typed_symbols[CallbackSymbol] = TypedSymbolsList ("Callback Functions")
        self.typed_symbols[FunctionMacroSymbol] = TypedSymbolsList ("Function Macros")
        self.typed_symbols[ConstantSymbol] = TypedSymbolsList ("Constants")
        self.typed_symbols[ExportedVariableSymbol] = TypedSymbolsList ("Exported Variables")
        self.typed_symbols[StructSymbol] = TypedSymbolsList ("Data Structures")
        self.typed_symbols[EnumSymbol] = TypedSymbolsList ("Enumerations")
        self.typed_symbols[AliasSymbol] = TypedSymbolsList ("Aliases")
        self.typed_symbols[SignalSymbol] = TypedSymbolsList ("Signals")
        self.typed_symbols[PropertySymbol] = TypedSymbolsList ("Properties")
        self.typed_symbols[VFunctionSymbol] = TypedSymbolsList ("Virtual Methods")
        self.typed_symbols[ClassSymbol] = TypedSymbolsList ("Classes")

        self.formatted_contents = None
        self.formatted_doc = ''

        new_sym_names = []
        for sym_name in self.symbol_names:
            sym = doc_tool.get_symbol(sym_name)
            if sym:
                self.resolve_symbol (sym)

            new_symbols = sum(doc_tool.doc_tree.symbol_added_signal(self, sym),
                    [])
            for symbol in new_symbols:
                doc_tool.doc_tree.add_to_symbol_map(self, symbol)
                new_sym_names.append(symbol.unique_name)
                self.resolve_symbol (symbol)

        self.symbol_names.extend(new_sym_names)

    def resolve_symbol (self, symbol):
        symbol.link.ref = "%s#%s" % (self.link.ref, symbol.unique_name)
        for l in symbol.get_extra_links():
            l.ref = "%s#%s" % (self.link.ref, l.id_)

        tsl = self.typed_symbols[type(symbol)]
        tsl.symbols.append (symbol)
        self.symbols.append (symbol)
        if type (symbol) in [ClassSymbol, StructSymbol] and symbol.comment:
            if symbol.comment.short_description:
                self.short_description = symbol.comment.short_description
            if symbol.comment.title:
                self.title = symbol.comment.title

    def get_short_description (self):
        return self.short_description or self.first_paragraph

    def get_title (self):
        return self.title or self.first_header or self.link.title

class ParsedHeader(object):
    def __init__(self, ast_node, original_destination):
        self.ast_node = ast_node
        self.original_destination = original_destination

class PageParser(object):
    def __init__(self, doc_tool, doc_tree, prefix):
        self.__cmp = CommonMark.Parser()
        self.__cmr = CommonMark.html.HtmlRenderer()
        self.well_known_names = {}
        self.doc_tree = doc_tree
        self.prefix = prefix
        self.doc_tool = doc_tool

    def register_well_known_name (self, wkn, callback):
        self.well_known_names[wkn] = callback

    def check_links(self, page, node, parent_node=None):
        if node.t == 'Link':
            if node.destination:
                path = os.path.join(self.prefix, node.destination)
                if not os.path.exists(path):
                    path = None
            else:
                path = None

            handler = self.well_known_names.get(node.destination)
            if handler:
                subpage, subfolder, extension_name = handler(self.doc_tree)
                page.subpages[subpage] = extension_name
                new_dest = os.path.splitext(os.path.basename(subpage))[0]
                if subfolder:
                    new_dest = subfolder + '/' + new_dest
                node.destination = '%s.html' % new_dest
            elif parent_node and parent_node.t == 'Heading' and path:
                if not path in self.doc_tree.seen_pages:
                    page.subpages[path] = page.extension_name
                    self.doc_tree.seen_pages.add (path)

                original_name = get_label(node)
                parsed_header = ParsedHeader(list(get_children(parent_node)), path)
                page.headers[original_name] = parsed_header
                node.destination = '%s.html' % os.path.splitext(node.destination)[0]

        elif (node.t == "Heading" and not page.first_header):
            page.first_header = get_label(node)

        elif (node.t == "Paragraph" and not page.first_paragraph):
            first_paragraph = ''
            for i in range (node.sourcepos[0][0], node.sourcepos[1][0] + 1):
                first_paragraph += linecache.getline(page.source_file, i)
            page.first_paragraph = first_paragraph

        for c in get_children(node):
            self.check_links (page, c, node)

    def parse_list (self, page, l):
        for c in get_children(l):
            for c2 in get_children(c):
                if c2.t == "Paragraph" and len (list(get_children(c2))) == 1:
                    if self.parse_para (page, c2):
                        c.unlink()

    def parse_para(self, page, paragraph):
        ic = paragraph.first_child

        if ic.t != "Link":
            return False

        label = get_label(ic)

        if not ic.destination and label:
            name = label.strip('[]() ')
            page.symbol_names.append(name)
            ic.destination = "not_an_actual_link_sorry"
            return True
        return False

    def parse(self, source_file, extension_name):
        if not os.path.exists(source_file):
            return None

        with io.open(source_file, 'r', encoding='utf-8') as f:
            contents = f.read()

        page = Page(source_file, extension_name)

        ast = self.__cmp.parse(contents)
        page.ast = ast

        for c in get_children(ast):
            if c.t == "List":
                self.parse_list(page, c)

        self.check_links(page, ast)

        return page

    def reparse(self, page):
        with io.open(page.source_file, 'r', encoding='utf-8') as f:
            contents = f.read()

        ast = self.__cmp.parse(contents)
        page.ast = ast

        page.symbol_names = []
        for c in get_children(ast):
            if c.t == "List":
                self.parse_list(page, c)

        self.check_links(page, ast)

    def parse_contents(self, page, contents):
        page.ast = self.__cmp.parse(contents)

    def _update_links (self, node):
        if node.t == 'Link':
            if not hasattr(node, 'original_dest'):
                node.original_dest = node.destination
                node.original_label = get_label(node)

            link = self.doc_tool.link_resolver.get_named_link(node.original_dest)
            if link and not node.original_label:
                set_label(self.__cmp, node, link.title)

            if link and link.get_link() is not None:
                node.destination = link.get_link()

        for c in get_children(node):
            self._update_links (c)

    def render (self, page):
        self._update_links (page.ast)
        return self.__cmr.render (page.ast) 

    def rename_headers(self, page, new_names):
        for original_name, parsed_header in page.headers.items():
            ast_node = parsed_header.ast_node
            page = self.doc_tree.get_page(parsed_header.original_destination)

            if page.title is not None:
                set_label(self.__cmp, ast_node[0], page.title)
            elif original_name in new_names:
                set_label(self.__cmp, ast_node[0], new_names[original_name])
            else:
                set_label (self.__cmp, ast_node[0], original_name)

            desc = page.get_short_description()
            if desc:
                first = True
                for c in get_children(ast_node[0].parent):
                    if not first:
                        c.unlink()
                    first = False

                desc = self.doc_tool.doc_parser.translate (desc)
                new_desc = self.__cmp.parse(u' — %s' % desc.encode ('utf-8'))
                for c in get_children(new_desc.first_child):
                    ast_node[0].parent.append_child(c)

class DocTree(object):
    def __init__(self, doc_tool, prefix):
        self.seen_pages = set({})
        self.page_parser = PageParser(doc_tool, self, prefix)

        self.pages_path = os.path.join(doc_tool.get_private_folder(), 'pages.p')
        self.symbol_maps_path = os.path.join(doc_tool.get_private_folder(),
                'symbol_maps.p')

        try:
            self.pages = pickle.load(open(self.pages_path, 'rb'))
        except:
            self.pages = {}

        try:
            self.previous_symbol_maps = pickle.load(open(self.symbol_maps_path, 'rb'))
        except:
            self.previous_symbol_maps = {}

        self.prefix = prefix
        self.symbol_added_signal = Signal()
        doc_tool.comment_updated_signal.connect(self.__comment_updated)
        doc_tool.symbol_updated_signal.connect(self.__symbol_updated)
        self.doc_tool = doc_tool
        self.symbol_maps = {}

    def get_page(self, name):
        return self.pages.get(name)

    def add_to_symbol_map(self, page, sym):
        symbol_map = self.symbol_maps.pop(sym.unique_name, {})
        symbol_map[page.source_file] = page
        self.symbol_maps[sym.unique_name] = symbol_map

    def symbol_has_moved(self, symbol_map, name):
        if not self.doc_tool.incremental:
            return False

        return set(symbol_map.keys()) != set(self.previous_symbol_maps.get(name,
            {}).keys())

    def update_symbol_maps(self):
        moved_symbols = set({})
        for page in self.pages.values():
            for name in page.symbol_names:
                symbol_map = self.symbol_maps.pop(name, {})
                symbol_map[page.source_file] = page
                self.symbol_maps[name] = symbol_map
                if self.symbol_has_moved(symbol_map, name):
                    moved_symbols.add(name)

        return moved_symbols

    def persist(self):
        pickle.dump(self.pages, open(self.pages_path, 'wb'))
        pickle.dump(self.symbol_maps, open(self.symbol_maps_path, 'wb')) 

    def build_tree (self, source_file, extension_name=None):
        page = None

        if source_file in self.pages:
            epage = self.pages[source_file]
            if extension_name == epage.extension_name:
                try:
                    mtime = os.path.getmtime(source_file)
                    if mtime == epage.mtime:
                        page = epage
                except OSError:
                    page = epage

        if not page:
            page = self.page_parser.parse(source_file, extension_name)

        self.pages[source_file] = page

        for subpage, extension_name in page.subpages.items():
            self.build_tree(subpage, extension_name=extension_name)

        return page

    def resolve_symbols(self, doc_tool, page):
        if page.is_stale:
            if page.mtime != -1 and not page.ast:
                self.page_parser.reparse(page)

            page.resolve_symbols(doc_tool)
        for pagename in page.subpages:
            cpage = self.pages[pagename]
            self.resolve_symbols(doc_tool, page=cpage)

    def __stale_symbol_pages (self, symbol_name):
        pages = self.symbol_maps.get(symbol_name, {})
        for page in pages.values():
            page.is_stale = True

    def __comment_updated(self, comment):
        self.__stale_symbol_pages(comment.name)

    def __symbol_updated(self, symbol):
        self.__stale_symbol_pages(symbol.unique_name)
