# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=too-many-lines

"""
Implements standalone markdown files parsing.
"""

import cPickle as pickle
import io
import linecache
import os
import urllib
import urlparse
from collections import OrderedDict
from collections import namedtuple
from collections import defaultdict

import yaml as pyyaml
import CommonMark

from hotdoc.core.doc_database import DocDatabase
from hotdoc.core.links import Link
from hotdoc.core.symbols import\
    (Symbol, FunctionSymbol, CallbackSymbol,
     FunctionMacroSymbol, ConstantSymbol, ExportedVariableSymbol,
     StructSymbol, EnumSymbol, AliasSymbol, SignalSymbol, PropertySymbol,
     VFunctionSymbol, ClassSymbol)
from hotdoc.utils.simple_signals import Signal
from hotdoc.utils.utils import OrderedSet
from hotdoc.utils.loggable import info, debug
from hotdoc.core.file_includer import add_md_includes, find_md_file


Yaml = namedtuple('Yaml', ['group_to_pages', 'page_to_meta'])


def _find_md_file_for_yaml_file(basename):
    if os.path.exists(basename + '.markdown'):
        return basename + '.markdown'
    if os.path.exists(basename + '.md'):
        return basename + '.md'
    return None


def _parse_yaml_folder(folder, yaml):
    for name in os.listdir(folder):
        fname = os.path.join(folder, name)
        if not os.path.isfile(fname):
            continue
        split_ext = os.path.splitext(name)
        if len(split_ext) != 2:
            continue
        ext = split_ext[1]
        basename = split_ext[0]
        if ext != '.yaml':
            continue

        md_file = _find_md_file_for_yaml_file(
            os.path.join(folder, basename))

        if md_file is None:
            continue

        with io.open(fname, 'r', encoding='utf-8') as _:
            contents = _.read()

        # FIXME: Ahem
        contents = contents.replace('\\#', '#')

        data = pyyaml.load(contents)
        group = data.get("guide-group")

        if group:
            yaml.group_to_pages[group].add(md_file)

        yaml.page_to_meta[basename] = data


def _parse_yaml_folders(folders):
    yaml = Yaml(group_to_pages=defaultdict(set), page_to_meta=dict())
    for folder in folders:
        _parse_yaml_folder(folder, yaml)
    return yaml


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
    """Represents an input page.
    Attributes:
        symbol_names: list, contains all the symbol names that will be
            documented in that page. Note that some extensions may
            provide extra symbols at resolution time, the list will thus
            be updated at that time. You can register to the
            `adding_symbol_signal` to be notified of additions.
        subpages: list, contains the absolute paths to all the valid
            markdown source files this page links to.
        link: hotdoc.core.links.Link, the link to that page.
        title: str, workaround to use the title of the first included
            ClassSymbol or StructSymbol as the title of that page,
            in case it did not have one of its own. Direct access
            is not recommended, use the `Page.get_title` method to
            get the preferred display name for that page.
        short_description: str, workaround to use the short description of the
            first included ClassSymbol or StructSymbol as the title of that
            page, in case it did not have one of its own. Direct access
            is not recommended, use the `Page.get_short_description` method to
            get the preferred summary for that page.
        first_header: str, the first header in the markdown source
            file. Mainly exposed to let PageParser provide it,
            direct access is not recommended, use the `Page.get_title`
            method to get the preferred display name for that
            page.
        first_paragraph: str, the first paragraph in the markdown
            source file. Mainly exposed to let PageParser provide it,
            direct access is not recommended, use the
            `Page.get_short_description` method to get the preferred summary
            for that page.
        source_file: str, the absolute path to the markdown file this page
            was constructed from.
        output_attrs: collections.defaultdict, a lightweight mechanism
            to permit data exchange between extensions and formatters.

            For example the html formatter will include any scripts listed
            in ['html']['scripts']:

            >>> page.output_attrs['html']['scripts'].add(self.script)

        extension_name: str, the name of the "parent extension" for
            that page, can be None, in which case the parent is the
            current DocRepo.
        is_stale: bool, whether that page will be reparsed and reformatted.
            this can be set to true for three reasons:

            * The source file of the page was modified.

            * A symbol (or its comment) contained in the page was modified

            * A symbol linked to by one or several symbols in that page
              was moved, and the links in that page need to be updated.

        ast: CommonMark.node, currently the only PageParser uses
            CommonMark, and as such the only type this attribute can have
            is this. This might change in the future. Note
            that the ast is not serialized, and reparsed each time the page
            needs to be rendered again.
        headers: dict, contains all the headers that pointed to valid
            markdown subpages, used to prettify these at format-time.

            For example, given this line in the source_file:
            `#### [my_sub_page](my_sub_page.markdown)` , the key stored here
            will be "my_sub_page", and the associated value will be the
            CommonMark.node of the header.
        reference_map: set, used to track all the link ids referred to
            in this page.
        typed_symbols: dict, soon to be deprecated.
        symbols: list, empty until resolve_symbols has been called. Symbol
            querying in the database is costly, and as such executed
            "just-in-time"
        formatted_contents: str, empty until DocRepo.format_page has been
            called, it then contains the html rendering of the ast, including
            the modifications made by PageParser, provided the page was stale.
        mtime: int, the modification time of the source file last time it was
            parsed.
    """
    # pylint: disable=too-many-instance-attributes

    resolving_symbol_signal = Signal()
    adding_symbol_signal = Signal()
    formatting_signal = Signal()

    def __init__(self, source_file, ast, extension_name):
        name = os.path.splitext(os.path.basename(source_file))[0]
        pagename = '%s.html' % name

        self.symbol_names = OrderedSet()
        self.topic_symbol_names = OrderedSet()
        self.topic = None
        self.subpages = OrderedDict({})
        self.link = Link(pagename, name, name)
        self.title = None
        self.short_description = None
        self.first_header = None
        self.first_paragraph = None
        self.source_file = source_file
        self.output_attrs = None
        self.extension_name = extension_name
        self.is_stale = True
        self.ast = ast
        self.headers = {}
        self.reference_map = set()
        self.typed_symbols = {}
        self.symbols = []
        self.formatted_contents = None
        self.detailed_description = None

        try:
            self.mtime = os.path.getmtime(source_file)
        except OSError:
            self.mtime = -1

    def __getstate__(self):
        return {'symbol_names': self.symbol_names,
                'topic_symbol_names': self.topic_symbol_names,
                'topic': self.topic,
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
                'detailed_description': None,
                'headers': {},
                'typed_symbols': {},
                'symbols': [],
                'formatted_contents': None,
                'is_stale': False,  # At pickle time, assume non-staleness
                'mtime': self.mtime}

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

    def add_symbol(self, unique_name, is_topic=False):
        """Adds a symbol name to the ordered set of symbol names contained
        in this page.

        Args:
            unique_name: str, the symbol name to add, if already present
            it will not be duplicated, and will keep the same position
            in the set of symbol names.
        """
        self.adding_symbol_signal(self, unique_name)
        self.symbol_names.add(unique_name)
        if is_topic:
            self.topic_symbol_names.add(unique_name)

    def resolve_symbols(self, doc_database, link_resolver):
        """
        When this method is called, the page's symbol names are queried
        from `doc_database`, and added to lists of actual symbols, sorted
        by symbol class.
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

        new_syms = []
        for sym_name in self.symbol_names:
            sym = doc_database.get_symbol(sym_name)
            self.__query_extra_symbols(sym, new_syms, link_resolver)

        for sym in new_syms:
            self.add_symbol(sym.unique_name)

    def format(self, formatter, link_resolver, output):
        """
        Banana banana
        """
        self.output_attrs = defaultdict(lambda: defaultdict(dict))
        formatter.prepare_page_attributes(self)
        Page.formatting_signal(self, formatter)
        self.reference_map = set()
        self.__format_symbols(formatter, link_resolver)
        self.detailed_description =\
            formatter.format_page(self)[0]
        formatter.write_page(self, output)

    def remove_subpage(self, source_file):
        """
        Banana banana
        """
        self.subpages.pop(source_file, None)
        for name, header in self.headers.items():
            if header.original_destination == source_file:
                header.ast_node[0].parent.unlink()
                self.headers.pop(name)
                break

    def __format_symbols(self, formatter, link_resolver):
        for symbol in self.symbols:
            if symbol is None:
                continue
            debug('Formatting symbol %s in page %s' % (
                symbol.unique_name, self.source_file), 'formatting')
            symbol.skip = not formatter.format_symbol(symbol, link_resolver)

    def __query_extra_symbols(self, sym, new_syms, link_resolver):
        if sym:
            new_symbols = sum(Page.resolving_symbol_signal(self, sym),
                              [])

            self.__resolve_symbol(sym, link_resolver)

            for symbol in new_symbols:
                new_syms.append(symbol)
                self.__query_extra_symbols(symbol, new_syms, link_resolver)

    def __resolve_symbol(self, symbol, link_resolver):
        symbol.resolve_links(link_resolver)

        symbol.link.ref = "%s#%s" % (self.link.ref, symbol.unique_name)

        for link in symbol.get_extra_links():
            link.ref = "%s#%s" % (self.link.ref, link.id_)

        tsl = self.typed_symbols[type(symbol)]
        tsl.symbols.append(symbol)
        self.symbols.append(symbol)
        # pylint: disable=unidiomatic-typecheck
        if type(symbol) in [ClassSymbol, StructSymbol] and symbol.comment:
            if symbol.comment.short_description:
                self.short_description = symbol.comment.short_description
            if symbol.comment.title:
                self.title = symbol.comment.title

        debug('Resolved symbol %s to page %s' %
              (symbol.display_name, self.link.ref), 'resolution')


# pylint: disable=too-many-instance-attributes
class PageParser(object):
    """Parses individual pages, detecting empty links to potential subpages.

    Creates Page objects.

    Attributes:
        renaming_page_link_signal: hotdoc.utils.simple_signals.Signal, emitted
            when about to prettify a navigational link in order to let
            listeners provide their own pretty title and summary.
    """

    def __init__(self, doc_tree, include_paths):
        self.renaming_page_link_signal = Signal()

        self.__cmp = CommonMark.Parser()
        self.__cmr = CommonMark.html.HtmlRenderer()
        self.__well_known_names = {}
        self.__doc_tree = doc_tree
        self.__seen_pages = set({})
        self.__include_paths = include_paths
        self.__yaml = _parse_yaml_folders(include_paths)
        self.__parsed_header_class = namedtuple('ParsedHeader',
                                                ['ast_node',
                                                 'original_destination'])

    def parse(self, source_file, extension_name):
        """
        Given a source file and a possible extension name,
        returns a parsed Page object. This function does not
        parse subpages, they are instead listed in the subpages
        attribute of the returned page.
        Args:
            source_file: str, path to the source file to parse
            extension_name: str, name of the extension responsible
                for this page. If None, the responsible entity is
                the `doc_repo.DocRepo` itself.
        """
        if not os.path.exists(source_file):
            return None

        debug('Parsing markdown file %s' % source_file, 'parsing')

        with io.open(source_file, 'r', encoding='utf-8') as _:
            contents = add_md_includes(_.read(), source_file,
                                       self.__include_paths, 0)

        ast = self.__cmp.parse(contents)
        page = Page(source_file, ast, extension_name)

        for _ in _get_children(ast):
            if _.t == "List":
                self.__parse_list_node(page, _)

        self.__check_links(page, ast)

        return page

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
        self.__well_known_names[wkn] = callback

    def format_page(self, page, link_resolver, formatter):
        """Returns the formatted page contents.

        Can only format to html for now.

        Args:
            page: hotdoc.core.doc_tree.Page, the page which contents
                have to be formatted.
        """
        self.__rename_page_links(page,
                                 formatter,
                                 link_resolver)
        self.__update_links(page.ast, link_resolver)
        return self.__cmr.render(page.ast)

    def __rename_page_links(self, page, formatter, link_resolver):
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
        if page.extension_name == 'core':
            return

        for original_name, parsed_header in page.headers.items():
            ast_node = parsed_header.ast_node
            page = self.__doc_tree.get_page(parsed_header.original_destination)

            if page.title is not None:
                _set_label(self.__cmp, ast_node[0], page.title)
            else:
                replacements = self.renaming_page_link_signal(self,
                                                              original_name)
                try:
                    rep = next(rep for rep in replacements if rep is not None)
                    _set_label(self.__cmp, ast_node[0], rep)
                except StopIteration:
                    _set_label(self.__cmp, ast_node[0], page.get_title() or
                               original_name)

            desc = page.get_short_description()

            if desc:
                first = True
                for _ in _get_children(ast_node[0].parent):
                    if not first:
                        _.unlink()
                    first = False

                desc = formatter.format_docstring(desc, link_resolver,
                                                  to_native=True)
                if desc:
                    new_desc = self.__cmp.parse(u' — %s' %
                                                desc.encode('utf-8'))
                    for _ in _get_children(new_desc.first_child):
                        ast_node[0].parent.append_child(_)

    def __add_subpage(self, cur_page, path):
        if path not in self.__seen_pages:
            cur_page.subpages[path] = cur_page.extension_name
            self.__seen_pages.add(path)
        else:
            print "Already seen", path

    # pylint: disable=too-many-locals
    def __parse_yaml_topics_link(self, cur_page, node):
        parent = node.parent
        if not parent:
            return False
        if not self.__yaml.group_to_pages:
            return False
        label = _get_label(node)
        if label:
            return False
        dest = urllib.unquote(node.destination)
        groups = dest.split()
        group_to_pages = self.__yaml.group_to_pages
        page_to_meta = self.__yaml.page_to_meta
        if not all(g in group_to_pages or g == u"#default" for g in groups):
            return False

        generated = u''

        for group in groups:
            # FIXME : add pages not referenced anywhere here
            if group == u'#default':
                continue
            # FIXME: Special formatting for first ?
            if group != u'#first':
                generated += '\n### %s\n\n' % group
            page_names = group_to_pages[group]
            for page_path in page_names:
                basename = os.path.basename(page_path)
                split_ext = os.path.splitext(basename)
                ref = split_ext[0] + '.html'
                page_yaml = page_to_meta[split_ext[0]]

                desc = page_yaml.get("description")
                if desc is not None:
                    desc = unicode(' '.join(desc.split()))
                    desc = u' — %s' % desc
                else:
                    desc = u''

                title = page_yaml.get("title")
                if not title:
                    title = basename

                self.__add_subpage(cur_page, page_path)
                generated += '\n#### [%s](%s)%s\n' % (title, ref, desc)

        generated_ast = self.__cmp.parse(generated)
        for new_node in _get_children(generated_ast):
            node.insert_before(new_node)

        node.unlink()
        return True

    def __find_md_file(self, dest):
        dest = urllib.unquote(dest)
        path = None
        for fname in (
                dest,
                dest + '.markdown',
                dest + '.md'):
            path = find_md_file(fname, self.__include_paths)
            if path:
                break
        return path

    def __parse_symbols_topic_link(self, page, node):
        topic = _get_label(node)
        _set_label(self.__cmp, node.parent, topic)
        page.topic = topic
        self.__doc_tree.add_topic_to_page(topic, page)

    # pylint: disable=too-many-branches
    def __check_links(self, page, node, parent_node=None):
        if node.t == 'Link':
            path = None
            if node.destination:
                # The rest of this sub-ast does not matter anymore
                if self.__parse_yaml_topics_link(page, node):
                    return
                if (node.parent and node.parent.t == 'Heading') or \
                        node.destination in self.__yaml.page_to_meta:
                    path = self.__find_md_file(node.destination)
            else:
                self.__parse_symbols_topic_link(page, node)
                return

            handler = self.__well_known_names.get(node.destination)
            if handler:
                res = handler(self.__doc_tree)
                if res is not None:
                    subpage, subfolder, extension_name = res
                    page.subpages[subpage] = extension_name
                    new_dest = os.path.splitext(os.path.basename(subpage))[0]
                    if subfolder:
                        new_dest = subfolder + '/' + new_dest
                    node.destination = '%s.html' % new_dest
            elif path:
                self.__add_subpage(page, path)

                original_name = _get_label(node)
                parsed_header = self.__parsed_header_class(
                    list(_get_children(parent_node)), path)
                page.headers[original_name] = parsed_header
                bname = os.path.basename(path)
                node.destination = '%s.html' %\
                    os.path.splitext(bname)[0]

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
            page.add_symbol(name)
            link_node.destination = "not_an_actual_link_sorry"
            return True
        return False

    def __check_yaml_meta(self, node):
        url_components = urlparse.urlparse(node.destination)
        if bool(url_components.netloc):
            return

        if node.destination in self.__yaml.page_to_meta:
            node.destination += ".html"
        else:
            md_file = self.__find_md_file(url_components.path)
            if md_file:
                basename = os.path.basename(md_file)
                split_ext = os.path.splitext(basename)
                node.destination = split_ext[0] + '.html'
                if url_components.fragment:
                    node.destination += '#' + url_components.fragment

    def __update_links(self, node, link_resolver):
        if node.t == 'Link':
            if not hasattr(node, 'original_dest'):
                node.original_dest = node.destination
                node.original_label = _get_label(node)

            link = link_resolver.get_named_link(
                node.original_dest)
            if link and not node.original_label:
                _set_label(self.__cmp, node, link.title)

            if link and link.get_link() is not None:
                node.destination = link.get_link()
            else:
                self.__check_yaml_meta(node)

        for _ in _get_children(node):
            self.__update_links(_, link_resolver)


class DocTree(object):
    """
    Responsible for parsing the
    standalone markdown files that will form the sructure of
    the output documentation.
    Attributes:
        page_parser: hotdoc.core.doc_tree.PageParser, the parser used to
            interpret and translate documentation source files. Currently
            the only implementation is a CommonMark-py parser, but the
            DocTree and PageParser classes were decoupled in order to
            allow implementing another parser pretty easily.
        pages: dict of hotdoc.core.doc_tree.Page, which the doc_tree is
            made of. Navigation is currently achieved by querying this
            dictionary for the names listed in each Page.subpages.
        reference_map: dict, link ids -> referencing pages
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, include_paths, private_folder, toplevel=True):
        self.page_parser = PageParser(self, include_paths)

        self.pages = {}
        self.reference_map = defaultdict(set)
        self.__topics_map = {}
        self.__incremental = False
        self.__current_page = None
        self.__symbol_maps = defaultdict(defaultdict)
        self.__pages_path = os.path.join(
            private_folder, 'pages.p')
        self.__symbol_maps_path = os.path.join(
            private_folder, 'symbol_maps.p')
        self.__topics_map_path = os.path.join(
            private_folder, 'topics_map.p')
        self.__reference_map_path = os.path.join(
            private_folder, 'reference_map.p')
        self.__root = None
        self.__parent_tree = None

        if toplevel:
            try:
                self.pages = pickle.load(open(
                    self.__pages_path, 'rb'))
                self.__previous_symbol_maps = pickle.load(open(
                    self.__symbol_maps_path, 'rb'))
                self.reference_map = pickle.load(open(
                    self.__reference_map_path, 'rb'))
                self.__topics_map = pickle.load(open(
                    self.__topics_map_path, 'rb'))
                self.__incremental = True
            except IOError:
                pass

            DocDatabase.comment_updated_signal.connect(self.__comment_updated)
            DocDatabase.comment_added_signal.connect(self.__comment_added)
            DocDatabase.symbol_updated_signal.connect(self.__symbol_updated)

    def build_tree(self, source_file, extension_name=None, parent_tree=None):
        """
        The main entry point, given a root source_file, this method
        will construct (or update) the complete doc_tree, including
        subtrees that may be provided by extensions.

        Args:
          source_file: str, The source file to start building the tree
            from, will recurse in potential subpages.
          extension_name: str, The extension in charge of handling this
            page and its subpages.
        """
        self.__parent_tree = parent_tree
        if parent_tree:
            info("Building subtree from %s" % source_file, "parsing")
        else:
            info("Building tree from %s" % source_file, "parsing")

        self.__do_build_tree(source_file, extension_name)
        moved_symbols = self.__update_symbol_maps()
        self.__root = self.pages[source_file]

        for symbol_id in moved_symbols:
            referencing_pages = self.reference_map.get(symbol_id, set())
            for pagename in referencing_pages:
                page = self.pages[pagename]
                if page:
                    page.is_stale = True

        return self.__root

    def format(self, link_resolver, output, extensions):
        """Banana banana
        """
        info('Formatting documentation tree', 'formatting')
        self.__setup_folder(output)

        Page.formatting_signal.connect(self.__formatting_page_cb)
        Link.resolving_link_signal.connect(self.__link_referenced_cb)

        for page in self.walk():
            self.__current_page = page
            extension = extensions[page.extension_name]
            extension.format_page(page, link_resolver, output)

        self.__create_navigation_script(output, extensions)

    def resolve_symbols(self, doc_database, link_resolver, page):
        """Will call resolve_symbols on all the stale subpages of the tree.
        Args:
          page: hotdoc.core.doc_tree.Page, the page to resolve symbols in,
          will recurse on potential subpages.
        """
        if page.is_stale:
            if page.mtime != -1 and page.ast is None:
                new_page = self.page_parser.parse(page.source_file,
                                                  page.extension_name)
                self.pages[page.source_file] = new_page
                self.__add_topic_symbols(page, new_page)
                page = new_page

            page.resolve_symbols(doc_database, link_resolver)
        for pagename in page.subpages:
            cpage = self.pages[pagename]
            self.resolve_symbols(doc_database, link_resolver, page=cpage)

    def get_page(self, name):
        """Getter to access DocTree's pages.

        Args:
            name: str, the full path to the source markdown file.

        Returns:
            hotdoc.core.doc_tree.Page: the page or None.
        """
        return self.pages.get(name)

    def get_pages_for_symbol(self, unique_name):
        """Getter to access all the pages where a symbol is contained.

        Listing symbols in multiple pages is not very well tested yet,
        and as such not recommended.

        Args:
            unique_name: str, the name of the symbol to lookup pages for.

        Returns:
            list of hotdoc.core.doc_tree.Page, that contain the symbol.
        """
        return self.__symbol_maps[unique_name]

    def walk(self, parent=None):
        """Generator that yields pages in infix order

        Args:
            parent: hotdoc.core.doc_tree.Page, optional, the page to start
                traversal from. If None, defaults to the root of the doc_tree.

        Yields:
            hotdoc.core.doc_tree.Page: the next page
        """
        if parent is None:
            yield self.__root
            parent = self.__root

        for cpage_name in parent.subpages:
            cpage = self.pages[cpage_name]
            yield cpage
            for page in self.walk(parent=cpage):
                yield page

    def persist(self):
        """
        Persist the doc_tree to hotdoc's private folder
        """
        pickle.dump(self.pages, open(self.__pages_path, 'wb'))
        pickle.dump(self.__symbol_maps, open(self.__symbol_maps_path, 'wb'))
        pickle.dump(self.__topics_map, open(self.__topics_map_path, 'wb'))
        pickle.dump(self.reference_map, open(self.__reference_map_path, 'wb'))

    def add_topic_to_page(self, topic, page):
        """
        Banana banana
        """
        self.__topics_map[topic] = page.source_file

    def update_pages(self, new_pages):
        """
        Banana banana
        """
        self.pages.update(new_pages)

    def __create_navigation_script(self, output, extensions):
        # Wrapping this is in a javascript file to allow
        # circumventing stupid chrome same origin policy
        formatter = extensions['core'].get_formatter('html')
        site_navigation = formatter.format_site_navigation(self.__root, self)
        path = os.path.join(output,
                            'assets',
                            'js',
                            'site_navigation.js')
        site_navigation = site_navigation.replace('\n', '')
        site_navigation = site_navigation.replace('"', '\\"')
        js_wrapper = 'site_navigation_downloaded_cb("'
        js_wrapper += site_navigation
        js_wrapper += '");'
        with open(path, 'w') as _:
            _.write(js_wrapper.encode('utf-8'))

    def __link_referenced_cb(self, link):
        self.reference_map[link.id_].add(
            self.__current_page.source_file)
        self.__current_page.reference_map.add(link.id_)
        return None

    def __formatting_page_cb(self, page, formatter):
        for link_id in page.reference_map:
            self.reference_map.get(link_id, set()).discard(page.source_file)
        return None

    # pylint: disable=no-self-use
    def __setup_folder(self, folder):
        if not os.path.exists(folder):
            os.mkdir(folder)

    def __add_to_symbol_map(self, page, unique_name):
        self.__symbol_maps[unique_name][page.source_file] = page

    def __symbol_has_moved(self, unique_name):
        if not self.__incremental:
            return False

        return set(self.__symbol_maps[unique_name].keys()) !=\
            set(self.__previous_symbol_maps[unique_name].keys())

    def __symbol_added_to_page(self, page, unique_name):
        self.__add_to_symbol_map(page, unique_name)

    def __update_symbol_maps(self):
        moved_symbols = set({})
        for page in self.pages.values():
            for name in page.symbol_names:
                self.__add_to_symbol_map(page, name)
                if self.__symbol_has_moved(name):
                    moved_symbols.add(name)

        Page.adding_symbol_signal.connect(self.__symbol_added_to_page)

        return moved_symbols

    def __try_merging_pages(self, page):
        if self.__parent_tree is None:
            return

        old_page = self.__parent_tree.pages.get(page.source_file)
        if not old_page:
            return

        debug("Merging page %s" % page.source_file, 'parsing')
        page.symbol_names |= old_page.symbol_names
        page.topic_symbol_names |= old_page.symbol_names
        page.is_stale |= old_page.is_stale

    def __do_build_tree(self, source_file, extension_name):
        page = None
        epage = None

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

        if epage and page != epage:
            self.__add_topic_symbols(epage, page)

        self.__try_merging_pages(page)

        self.pages[source_file] = page

        for subpage, extension_name in page.subpages.items():
            self.__do_build_tree(subpage, extension_name=extension_name)

    def __stale_symbol_pages(self, symbol_name):
        pages = self.__symbol_maps.get(symbol_name, {})
        for page in pages.values():
            if not page.is_stale:
                debug('staling %s' % page.source_file)
            page.is_stale = True

    def __check_topics(self, comment):
        topic_tag = comment.tags.get('topic')
        if not topic_tag:
            return

        pagename = self.__topics_map.get(topic_tag.value)
        if not pagename:
            return

        page = self.pages.get(pagename)

        if not page:
            return

        page.add_symbol(comment.name, is_topic=True)

    def __add_topic_symbols(self, epage, page):
        if epage.topic == page.topic:
            for name in epage.topic_symbol_names:
                page.add_symbol(name)

    # pylint: disable=unused-argument
    def __comment_added(self, doc_db, comment):
        self.__check_topics(comment)

    # pylint: disable=unused-argument
    def __comment_updated(self, doc_db, comment):
        self.__check_topics(comment)
        self.__stale_symbol_pages(comment.name)

    # pylint: disable=unused-argument
    def __symbol_updated(self, doc_db, symbol):
        self.__stale_symbol_pages(symbol.unique_name)
