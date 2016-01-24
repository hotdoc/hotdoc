# -*- coding: utf-8 -*-
"""
Implements standalone markdown files parsing.
"""

import cPickle as pickle
import io
import linecache
import os
from collections import OrderedDict
from collections import namedtuple
from collections import defaultdict

import CommonMark
from hotdoc.core.links import Link
from hotdoc.core.symbols import\
    (Symbol, FunctionSymbol, CallbackSymbol,
     FunctionMacroSymbol, ConstantSymbol, ExportedVariableSymbol,
     StructSymbol, EnumSymbol, AliasSymbol, SignalSymbol, PropertySymbol,
     VFunctionSymbol, ClassSymbol)
from hotdoc.utils.simple_signals import Signal


def _get_children(node, recursive=False):
    if not recursive:
        child = node.first_child
        while child:
            nxt = child.nxt
            yield child
            child = nxt
    else:
        walker = node.walker()
        nxt = walker.nxt()
        while nxt is not None:
            yield nxt['node']
            nxt = walker.nxt()


def _get_label(link, recursive=False):
    return ''.join(_.literal or '' for _ in _get_children(link, recursive))


def _set_label(parser, node, text):
    for _ in _get_children(node):
        _.unlink()

    new_label = parser.parse(text)

    # We only want Document -> Paragraph -> children
    for _ in _get_children(new_label.first_child):
        node.append_child(_)


class Page(object):
    """
    Represents an input page.
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, source_file, extension_name):
        name = os.path.splitext(os.path.basename(source_file))[0]
        pagename = '%s.html' % name

        self.symbol_names = []
        self.subpages = OrderedDict({})
        self.link = Link(pagename, name, name)
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
        self.typed_symbols = {}
        self.symbols = []
        self.formatted_doc = ''
        self.formatted_contents = None

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
                'typed_symbols': {},
                'symbols': [],
                'formatted_doc': self.formatted_doc,
                'formatted_contents': None,
                'is_stale': False,  # At pickle time, assume non-staleness
                'mtime': self.mtime}

    def resolve_symbols(self, doc_tool):
        """
        When this method is called, the page's symbol names are queried
        from `doc_tool`, and added to lists of actual symbols, sorted
        by symbol class.
        Args:
            doc_tool: hotdoc.core.doc_tool.DocTool, the main doc_tool instance
        """
        typed_symbols_list = namedtuple(
            'TypedSymbolsList', ['name', 'symbols'])
        self.typed_symbols[Symbol] = typed_symbols_list('FIXME symbols', [])
        self.typed_symbols[FunctionSymbol] = typed_symbols_list(
            "Functions", [])
        self.typed_symbols[CallbackSymbol] = typed_symbols_list(
            "Callback Functions", [])
        self.typed_symbols[FunctionMacroSymbol] = typed_symbols_list(
            "Function Macros", [])
        self.typed_symbols[ConstantSymbol] = typed_symbols_list(
            "Constants", [])
        self.typed_symbols[ExportedVariableSymbol] = typed_symbols_list(
            "Exported Variables", [])
        self.typed_symbols[StructSymbol] = typed_symbols_list(
            "Data Structures", [])
        self.typed_symbols[EnumSymbol] = typed_symbols_list("Enumerations", [])
        self.typed_symbols[AliasSymbol] = typed_symbols_list("Aliases", [])
        self.typed_symbols[SignalSymbol] = typed_symbols_list("Signals", [])
        self.typed_symbols[PropertySymbol] = typed_symbols_list(
            "Properties", [])
        self.typed_symbols[VFunctionSymbol] = typed_symbols_list(
            "Virtual Methods", [])
        self.typed_symbols[ClassSymbol] = typed_symbols_list("Classes", [])

        new_sym_names = []
        for sym_name in self.symbol_names:
            sym = doc_tool.get_symbol(sym_name)
            if sym:
                self.__resolve_symbol(sym)

            new_symbols = sum(doc_tool.doc_tree.symbol_added_signal(self, sym),
                              [])
            for symbol in new_symbols:
                doc_tool.doc_tree.add_to_symbol_map(self, symbol.unique_name)
                new_sym_names.append(symbol.unique_name)
                self.__resolve_symbol(symbol)

        self.symbol_names.extend(new_sym_names)

    def __resolve_symbol(self, symbol):
        symbol.link.ref = "%s#%s" % (self.link.ref, symbol.unique_name)
        for _ in symbol.get_extra_links():
            _.ref = "%s#%s" % (self.link.ref, _.id_)

        tsl = self.typed_symbols[type(symbol)]
        tsl.symbols.append(symbol)
        self.symbols.append(symbol)
        # pylint: disable=unidiomatic-typecheck
        if type(symbol) in [ClassSymbol, StructSymbol] and symbol.comment:
            if symbol.comment.short_description:
                self.short_description = symbol.comment.short_description
            if symbol.comment.title:
                self.title = symbol.comment.title

    def get_short_description(self):
        """
        Returns a string suitable for displaying as a summary, for example
        in a different page.
        Returns:
            str: the short description.
        """
        return self.short_description or self.first_paragraph

    def get_title(self):
        """
        Returns the preferred title to use when referring to that page
        from another page.
        Returns:
            str: the preferred title
        """
        return self.title or self.first_header or self.link.title


# pylint: disable=too-many-instance-attributes
class PageParser(object):
    """
    Parses individual pages, detecting empty links to potential subpages.

    Creates Page objects.
    """

    def __init__(self, doc_tool, doc_tree, prefix):
        self.__cmp = CommonMark.Parser()
        self.__cmr = CommonMark.html.HtmlRenderer()
        self.well_known_names = {}
        self.doc_tree = doc_tree
        self.prefix = prefix
        self.doc_tool = doc_tool
        self.renaming_page_link_signal = Signal()
        self.__parsed_header_class = namedtuple('ParsedHeader',
                                                ['ast_node',
                                                 'original_destination'])

    def register_well_known_name(self, wkn, callback):
        """
        Allows extensions to register hooks to declare that a given page
        and its potential subpages are handled by this extension (this
        allows defining custom formatters for example).
        Args:
            wkn: str, the well-known-name to register
                (for example "python-api")
            callback: callable, a callable to execute when `wkn` is
                encountered.
                It is expected to accept the instance of the current DocTree,
                and to return a three-tuple made of:
                name of the subpage,
                possible subfolder,
                name of the handling extension
        """
        self.well_known_names[wkn] = callback

    def __check_links(self, page, node, parent_node=None):
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
                if path not in self.doc_tree.seen_pages:
                    page.subpages[path] = page.extension_name
                    self.doc_tree.seen_pages.add(path)

                original_name = _get_label(node)
                parsed_header = self.__parsed_header_class(
                    list(_get_children(parent_node)), path)
                page.headers[original_name] = parsed_header
                node.destination = '%s.html' %\
                    os.path.splitext(node.destination)[0]

        elif node.t == "Heading" and not page.first_header:
            page.first_header = _get_label(node)

        elif node.t == "Paragraph" and not page.first_paragraph:
            first_paragraph = ''
            for i in range(node.sourcepos[0][0], node.sourcepos[1][0] + 1):
                first_paragraph += linecache.getline(page.source_file, i)
            page.first_paragraph = first_paragraph

        for _ in _get_children(node):
            self.__check_links(page, _, node)

    def __parse_list_node(self, page, list_node):
        for child in _get_children(list_node):
            for grandchild in _get_children(child):
                if grandchild.t == "Paragraph" and\
                        len(list(_get_children(grandchild))) == 1:
                    if self.__parse_para(page, grandchild):
                        child.unlink()

    # This is part of a parsing mechanism which does use self.
    # pylint: disable=no-self-use
    def __parse_para(self, page, paragraph):
        if paragraph.first_child.t != "Link":
            return False

        link_node = paragraph.first_child

        label = _get_label(link_node)

        if not link_node.destination and label:
            name = label.strip('[]() ')
            page.symbol_names.append(name)
            link_node.destination = "not_an_actual_link_sorry"
            return True
        return False

    def parse(self, source_file, extension_name, page=None):
        """
        Given a source file and a possible extension name,
        returns a parsed Page object. This function does not
        parse subpages, they are instead listed in the subpages
        attribute of the returned page.
        Args:
            source_file: str, path to the source file to parse
            extension_name: str, name of the extension responsible
                for this page. If None, the responsible entity is
                the DocTool itself.
            page: hotdoc.core.doc_tree.Page, An existing page can be
                passed here to update it instead of creating a new one.
        """
        if not os.path.exists(source_file):
            return None

        with io.open(source_file, 'r', encoding='utf-8') as _:
            contents = _.read()

        if page is None:
            page = Page(source_file, extension_name)

        ast = self.__cmp.parse(contents)
        page.ast = ast
        page.symbol_names = []

        for _ in _get_children(ast):
            if _.t == "List":
                self.__parse_list_node(page, _)

        self.__check_links(page, ast)

        return page

    def __update_links(self, node):
        if node.t == 'Link':
            if not hasattr(node, 'original_dest'):
                node.original_dest = node.destination
                node.original_label = _get_label(node)

            link = self.doc_tool.link_resolver.get_named_link(
                node.original_dest)
            if link and not node.original_label:
                _set_label(self.__cmp, node, link.title)

            if link and link.get_link() is not None:
                node.destination = link.get_link()

        for _ in _get_children(node):
            self.__update_links(_)

    def render(self, page):
        """Returns the formatted page contents.

        Can only format to html for now.
        Args:
            page: hodoc.core.doc_tree.Page, the page which contents
                have to be formatted.
        """
        self.__update_links(page.ast)
        return self.__cmr.render(page.ast)

    def rename_page_links(self, page):
        """Prettifies the intra-documentation page links.

        For example a link to a valid markdown page such as:

        ``[my_other_page](my_other_page.markdown)``

        will be updated to:

        ``[My Other Page](my_other_page.markdown) - my potential short
        description``

        if my_other_page.markdown correctly exposes a custom title and
        a short description.

        Args:
            page: hotdoc.core.doc_tree.Page, the page to rename navigational
                links in.
        """
        for original_name, parsed_header in page.headers.items():
            ast_node = parsed_header.ast_node
            page = self.doc_tree.get_page(parsed_header.original_destination)

            if page.title is not None:
                _set_label(self.__cmp, ast_node[0], page.title)
            else:
                replacements = self.renaming_page_link_signal(self,
                                                              original_name)
                try:
                    rep = next(rep for rep in replacements if rep is not None)
                    _set_label(self.__cmp, ast_node[0], rep)
                except StopIteration:
                    _set_label(self.__cmp, ast_node[0], original_name)

            desc = page.get_short_description()
            if desc:
                first = True
                for _ in _get_children(ast_node[0].parent):
                    if not first:
                        _.unlink()
                    first = False

                desc = self.doc_tool.doc_parser.translate(desc)
                new_desc = self.__cmp.parse(u' — %s' % desc.encode('utf-8'))
                for _ in _get_children(new_desc.first_child):
                    ast_node[0].parent.append_child(_)


class DocTree(object):
    """
    Responsible for parsing the
    standalone markdown files that will form the sructure of
    the output documentation.
    Attributes:
      prefix: str, The prefix in which markdown files are looked up
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, doc_tool, prefix):
        self.seen_pages = set({})
        self.page_parser = PageParser(doc_tool, self, prefix)

        self.pages_path = os.path.join(
            doc_tool.get_private_folder(), 'pages.p')
        self.symbol_maps_path = os.path.join(doc_tool.get_private_folder(),
                                             'symbol_maps.p')

        try:
            self.pages = pickle.load(open(self.pages_path, 'rb'))
        except IOError:
            self.pages = {}

        try:
            self.previous_symbol_maps = pickle.load(
                open(self.symbol_maps_path, 'rb'))
        except IOError:
            self.previous_symbol_maps = defaultdict(defaultdict)

        self.symbol_maps = defaultdict(defaultdict)

        self.prefix = prefix
        self.symbol_added_signal = Signal()
        doc_tool.comment_updated_signal.connect(self.__comment_updated)
        doc_tool.symbol_updated_signal.connect(self.__symbol_updated)
        self.doc_tool = doc_tool

    def get_page(self, name):
        """
        Banana banana
        """
        return self.pages.get(name)

    def get_pages_for_symbol(self, unique_name):
        """
        Banana banana
        """
        return self.symbol_maps[unique_name]

    def add_to_symbol_map(self, page, unique_name):
        """
        Banana banana
        """
        self.symbol_maps[unique_name][page.source_file] = page

    def __symbol_has_moved(self, unique_name):
        if not self.doc_tool.incremental:
            return False

        return set(self.symbol_maps[unique_name].keys()) !=\
            set(self.previous_symbol_maps[unique_name].keys())

    def update_symbol_maps(self):
        """
        Banana banana
        """
        moved_symbols = set({})
        for page in self.pages.values():
            for name in page.symbol_names:
                self.add_to_symbol_map(page, name)
                if self.__symbol_has_moved(name):
                    moved_symbols.add(name)

        return moved_symbols

    def persist(self):
        """
        Persist the doc_tree to the doc_tool's private folder
        """
        pickle.dump(self.pages, open(self.pages_path, 'wb'))
        pickle.dump(self.symbol_maps, open(self.symbol_maps_path, 'wb'))

    def build_tree(self, source_file, extension_name=None):
        """
        Banana banana.
        Args:
          source_file: str, The source file to start building the tree
            from, will recurse in potential subpages.
          extension_name: str, The extension in charge of handling this
            page and its subpages.
        """
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
        """Will call resolve_symbols on all the stale subpages of the tree.
        Args:
          doc_tool: hotdoc.core.doc_tool.DocTool, the main doc_tool instance
          page: hotdoc.core.doc_tree.Page, the page to resolve symbols in,
          will recurse on potential subpages.
        """
        if page.is_stale:
            if page.mtime != -1 and not page.ast:
                self.page_parser.parse(page.source_file, page.extension_name,
                                       page)

            page.resolve_symbols(doc_tool)
        for pagename in page.subpages:
            cpage = self.pages[pagename]
            self.resolve_symbols(doc_tool, page=cpage)

    def __stale_symbol_pages(self, symbol_name):
        pages = self.symbol_maps.get(symbol_name, {})
        for page in pages.values():
            page.is_stale = True

    def __comment_updated(self, comment):
        self.__stale_symbol_pages(comment.name)

    def __symbol_updated(self, symbol):
        self.__stale_symbol_pages(symbol.unique_name)
