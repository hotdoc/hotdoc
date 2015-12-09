# -*- coding: utf-8 -*-

import CommonMark
import os
import cPickle as pickle
from xml.sax.saxutils import unescape

from ..utils.simple_signals import Signal

from .symbols import *
from .links import Link

class TypedSymbolsList (object):
    def __init__ (self, name):
        self.name = name
        self.symbols = []

class Page(object):
    def __init__(self, source_file):
        name = os.path.splitext(os.path.basename(source_file))[0]
        pagename = '%s.html' % name

        self.symbol_names = []
        self.subpages = set({})
        self.link = Link (pagename, name, name) 
        self.title = None
        self.short_description = None
        self.source_file = source_file
        self.extension_name = None
        try:
            self.mtime = os.path.getmtime(source_file)
        except OSError:
            self.mtime = -1

        self.is_stale = True
        self.ast = None
        self.headers = {}

    def __getstate__(self):
        return {'symbol_names': self.symbol_names,
                'subpages': self.subpages,
                'link': self.link,
                'title': self.title,
                'short_description': self.short_description,
                'source_file': self.source_file,
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
        if not '#' in symbol.link.ref:
            symbol.link.ref = '%s#%s' % (self.link.ref, symbol.link.ref)
        for l in symbol.get_extra_links():
            if not '#' in l.ref:
                l.ref = '%s#%s' % (self.link.ref, l.ref)
        tsl = self.typed_symbols[type(symbol)]
        tsl.symbols.append (symbol)
        self.symbols.append (symbol)
        if type (symbol) == ClassSymbol and symbol.comment:
            if symbol.comment.short_description:
                self.short_description = symbol.comment.short_description
            if symbol.comment.title:
                self.title = symbol.comment.title

    def get_short_description (self):
        return self.short_description

    def get_title (self):
        return self.title

class ParsedHeader(object):
    def __init__(self, ast_node, original_destination):
        self.ast_node = ast_node
        self.original_destination = original_destination

class PageParser(object):
    def __init__(self, doc_tool, doc_tree, prefix):
        self.__cmp = CommonMark.DocParser()
        self.__cmr = CommonMark.HTMLRenderer()
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
                subpage = handler(self.doc_tree)
                page.subpages.add (subpage)
                new_dest = os.path.splitext(os.path.basename(subpage))[0]
                node.destination = '%s.html' % new_dest
            elif parent_node and parent_node.t == 'ATXHeader' and path:
                if not path in self.doc_tree.seen_pages:
                    page.subpages.add (path)
                    self.doc_tree.seen_pages.add (path)

                original_name = node.label[0].c
                parsed_header = ParsedHeader(parent_node.inline_content, path)
                page.headers[original_name] = parsed_header
                node.destination = '%s.html' % os.path.splitext(node.destination)[0]

        for c in node.inline_content:
            self.check_links (page, c, node)
        for c in node.children:
            self.check_links (page, c, node)

    def parse_list (self, page, l):
        non_symbol_children = list(l.children)
        for c in l.children:
            for c2 in c.children:
                if c2.t == "Paragraph" and len (c2.inline_content) == 1:
                    if self.parse_para (page, c2):
                        non_symbol_children.remove(c)
        l.children = non_symbol_children

    def parse_para(self, page, paragraph):
        ic = paragraph.inline_content[0]

        if ic.t != "Link":
            return False

        if not ic.destination and ic.label:
            name = paragraph.strings[0].strip('[]() ')
            page.symbol_names.append(name)
            ic.destination = "not_an_actual_link_sorry"
            return True
        return False

    def parse(self, source_file):
        if not os.path.exists(source_file):
            return None

        with open(source_file, 'r') as f:
            contents = f.read()

        page = Page(source_file)

        ast = self.__cmp.parse(contents)
        page.ast = ast

        for c in ast.children:
            if c.t == "List":
                self.parse_list(page, c)

        self.check_links(page, ast)

        return page

    def reparse(self, page):
        with open(page.source_file, 'r') as f:
            contents = f.read()

        ast = self.__cmp.parse(contents)
        page.ast = ast

        page.symbol_names = []
        for c in ast.children:
            if c.t == "List":
                self.parse_list(page, c)

        self.check_links(page, ast)

    def parse_contents(self, page, contents):
        page.ast = self.__cmp.parse(contents)

    def _update_links (self, node):
        if node.t == 'Link':
            if not hasattr(node, 'original_dest'):
                node.original_dest = node.destination
                node.original_label = node.label

            link = self.doc_tool.link_resolver.get_named_link(node.original_dest)
            if link and not node.original_label:
                node.label = []
                name_block = CommonMark.CommonMark.Block()
                name_block.c = link.title
                name_block.t = 'Str'
                node.label.append(name_block)
            if link and link.get_link() is not None:
                node.destination = link.get_link()

        for c in node.inline_content:
            self._update_links (c)
        for c in node.children:
            self._update_links (c)

    def render (self, page):
        self._update_links (page.ast)
        return self.__cmr.render (page.ast) 

    def rename_headers(self, page, new_names):
        for original_name, parsed_header in page.headers.items():
            ast_node = parsed_header.ast_node
            page = self.doc_tree.get_page(parsed_header.original_destination)

            title = page.get_title()

            if title is not None:
                ast_node[0].label[0].c = title
            elif original_name in new_names:
                ast_node[0].label[0].c = new_names[original_name]

            desc = page.get_short_description()
            if desc:
                del ast_node[1:]
                desc = self.doc_tool.doc_parser.translate (desc)
                docstring = unescape (desc)
                desc = u' — %s' % desc.encode ('utf-8')
                sub_ast = self.__cmp.parse (desc)

                # I know, very specific naming
                for thing in sub_ast.children:
                    for other_thing in thing.inline_content:
                        ast_node.append (other_thing)

class DocTree(object):
    def __init__(self, doc_tool, prefix):
        self.seen_pages = set({})
        self.page_parser = PageParser(doc_tool, self, prefix)

        self.pages_path = os.path.join(doc_tool.get_private_folder(), 'pages.p')
        try:
            self.pages = pickle.load(open(self.pages_path, 'rb'))
        except:
            self.pages = {}
        self.prefix = prefix
        self.symbol_added_signal = Signal()
        doc_tool.comment_updated_signal.connect(self.__comment_updated)
        doc_tool.symbol_updated_signal.connect(self.__symbol_updated)
        self.root = None
        self.symbol_maps = {}

    def get_page(self, name):
        return self.pages.get(name)

    def add_to_symbol_map(self, page, sym):
        symbol_map = self.symbol_maps.pop(sym.unique_name, {})
        symbol_map[page.source_file] = page
        self.symbol_maps[sym.unique_name] = symbol_map

    def fill_symbol_maps(self):
        for page in self.pages.values():
            for name in page.symbol_names:
                symbol_map = self.symbol_maps.pop(name, {})
                symbol_map[page.source_file] = page
                self.symbol_maps[name] = symbol_map

    def persist(self):
        pickle.dump(self.pages, open(self.pages_path, 'wb'))

    def build_tree (self, source_file, extension_name=None):
        page = None

        if source_file in self.pages:
            epage = self.pages[source_file]
            extension_name = epage.extension_name
            try:
                mtime = os.path.getmtime(source_file)
                if mtime == epage.mtime:
                    page = epage
            except OSError:
                page = epage

        if not page:
            page = self.page_parser.parse(source_file)
            page.extension_name = extension_name

        self.pages[source_file] = page


        for subpage in page.subpages:
            self.build_tree(subpage, extension_name=extension_name)

        self.root = page

        return page

    def resolve_symbols(self, doc_tool, page=None):
        if page is None:
            page = self.root

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
