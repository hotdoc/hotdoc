import CommonMark
import os
import cPickle as pickle

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
        self.title = ''
        self.short_description = ''
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
                'is_stale': self.is_stale,
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

        for sym_name in self.symbol_names:
            sym = doc_tool.get_symbol(sym_name)
            if sym:
                self.resolve_symbol (sym)

            new_symbols = sum(doc_tool.doc_tree.symbol_added_signal(self, sym),
                    [])
            for symbol in new_symbols:
                self.resolve_symbol (symbol)

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
            handler = self.well_known_names.get(node.destination)
            if handler:
                subpage = handler(self.doc_tree)
                page.subpages.add (subpage)
                node.destination = '%s.html' % subpage
            elif parent_node and parent_node.t == 'ATXHeader' and node.destination and \
                    os.path.exists(os.path.join(self.prefix, node.destination)):
                path = os.path.join(self.prefix, node.destination)
                if not path in self.doc_tree.seen_pages:
                    page.subpages.add (path)
                    self.doc_tree.seen_pages.add (path)

                original_name = node.label[0].c
                page.headers[original_name] = node
                node.destination = '%s.html' % os.path.splitext(node.destination)[0]

        for c in node.inline_content:
            self.check_links (page, c, node)
        for c in node.children:
            self.check_links (page, c, node)

    def parse_list (self, page, l):
        for c in l.children:
            for c2 in c.children:
                if c2.t == "Paragraph" and len (c2.inline_content) == 1:
                    self.parse_para (page, c2)

    def parse_para(self, page, paragraph):
        ic = paragraph.inline_content[0]

        if ic.t != "Link":
            return

        if not ic.destination and ic.label:
            name = paragraph.strings[0].strip('[]() ')
            page.symbol_names.append(name)
            ic.destination = "not_an_actual_link_sorry"

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

        self.check_links(page, ast)

    def parse_contents(self, page, contents):
        page.ast = self.__cmp.parse(contents)

    def _update_links (self, node):
        if node.t == 'Link':
            link = self.doc_tool.link_resolver.get_named_link (node.destination)
            node.label[-1].c += ' '
            if link and link.get_link() is not None:
                node.destination = link.get_link()

        for c in node.inline_content:
            self._update_links (c)
        for c in node.children:
            self._update_links (c)

    def render (self, page):
        print page.source_file
        self._update_links (page.ast)
        return self.__cmr.render (page.ast) 

    def rename_headers(self, page, new_names):
        for original_name, elem in page.headers.items():
            if original_name in new_names:
                elem.label[0].c = new_names.get(original_name)

class DocTree(object):
    def __init__(self, doc_tool, prefix):
        self.seen_pages = set({})
        self.page_parser = PageParser(doc_tool, self, prefix)
        try:
            self.pages = pickle.load(open('pages.p', 'rb'))
        except:
            self.pages = {}
        self.prefix = prefix
        self.symbol_added_signal = Signal()
        self.doc_tool = doc_tool
        self.root = None

    def print_tree (self, page, level=0):
        if level == 0:
            self.walked_pages = set({})

        print '  ' * level + page.source_file, page.extension_name

        self.walked_pages.add(page.source_file)
        if page.subpages:
            for subpage in page.subpages:
                if subpage in self.walked_pages:
                    print '  ' * (level + 1) + subpage, '(already seen)'
                else:
                    cpage = self.pages[subpage]
                    self.print_tree(cpage, level + 1)

    def persist(self):
        pickle.dump(self.pages, open('pages.p', 'wb'))

    def build_tree (self, source_file, extension_name=None):
        page = None

        if source_file in self.pages:
            epage = self.pages[source_file]
            try:
                mtime = os.path.getmtime(source_file)
                if mtime == epage.mtime:
                    page = epage
                    page.is_stale = False
            except OSError:
                page = epage
                if page.mtime == -1:
                    page.is_stale = False

        if not page:
            page = self.page_parser.parse(source_file)
            page.extension_name = extension_name

        self.pages[source_file] = page


        for subpage in page.subpages:
            self.build_tree(subpage, extension_name=extension_name)

        self.root = page

        return page

    def resolve_symbols(self, page=None):
        if page is None:
            page = self.root

        if self.doc_tool.page_is_stale(page):
            page.resolve_symbols(self.doc_tool)
        for pagename in page.subpages:
            cpage = self.pages[pagename]
            self.resolve_symbols(cpage)
