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
import io
import re
import os
from urllib.parse import urlparse
import pickle
from collections import namedtuple, defaultdict, OrderedDict

# pylint: disable=import-error
import yaml
from yaml.constructor import ConstructorError
from schema import Schema, SchemaError, Optional, And

from hotdoc.utils.utils import id_from_text
from hotdoc.core.inclusions import find_file, resolve
from hotdoc.core.symbols import Symbol, StructSymbol, ClassSymbol,\
    InterfaceSymbol, AliasSymbol
from hotdoc.core.links import Link
from hotdoc.core.exceptions import HotdocSourceException, InvalidPageMetadata
from hotdoc.core.comment import Comment
# pylint: disable=no-name-in-module
from hotdoc.parsers import cmark
from hotdoc.utils.utils import OrderedSet, all_subclasses
from hotdoc.utils.signals import Signal
from hotdoc.utils.loggable import info, debug, warn, error, Logger


def _no_duplicates_constructor(loader, node, deep=False):
    """Check for duplicate keys."""

    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        value = loader.construct_object(value_node, deep=deep)
        if key in mapping:
            raise ConstructorError("while constructing a mapping",
                                   node.start_mark,
                                   "found duplicate key (%s)" % key,
                                   key_node.start_mark)
        mapping[key] = value

    return loader.construct_mapping(node, deep)


yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                     _no_duplicates_constructor)


OverridePage = namedtuple('OverridePage', ['source_file', 'file'])


class TreeNoSuchPageException(HotdocSourceException):
    """
    Raised when a subpage listed in the sitemap file could not be found
    in any of the include paths.
    """
    pass


Logger.register_error_code('no-such-subpage', TreeNoSuchPageException,
                           domain='doc-tree')
Logger.register_warning_code('invalid-page-metadata', InvalidPageMetadata,
                             domain='doc-tree')
Logger.register_warning_code('markdown-bad-link', HotdocSourceException)


PageResolutionResult = namedtuple('PageResolutionResult',
                                  ['found', 'source', 'generation_source',
                                   'extension_name'])


# pylint: disable=too-many-instance-attributes
class Page:
    "Banana banana"
    meta_schema = {Optional('title'): And(str, len),
                   Optional('symbols'): Schema([And(str, len)]),
                   Optional('private-symbols'): Schema([And(str, len)]),
                   Optional('short-description'): And(str, len),
                   Optional('description'): And(str, len),
                   Optional('render-subpages'): bool,
                   Optional('auto-sort'): bool,
                   Optional('full-width'): bool,
                   Optional('see-also'): And(str, len),
                   Optional('extra'): Schema({str: object}),
                   Optional('thumbnail'): And(str, len)}

    # pylint: disable=too-many-arguments
    def __init__(self, source_file, ast, output_path, project_name, meta=None,
                 raw_contents=None):
        "Banana banana"
        assert source_file
        basename = os.path.basename(source_file)
        name = os.path.splitext(basename)[0]
        ref = os.path.join(output_path,
                           re.sub(r'\W+', '-', os.path.splitext(basename)[0]))
        pagename = '%s.html' % ref

        self.ast = ast
        self.extension_name = None
        self.source_file = source_file
        self.raw_contents = raw_contents
        self.comment = None
        self.generated = False
        self.pre_sorted = False
        self.output_attrs = None
        self.subpages = OrderedSet()
        self.symbols = []
        self.private_symbols = []
        self.typed_symbols = OrderedDict()
        self.by_parent_symbols = OrderedDict()
        self.is_stale = True
        self.formatted_contents = None
        self.detailed_description = None
        self.build_path = None
        self.thumbnail = None
        self.project_name = project_name
        self.cached_paths = OrderedSet()

        meta = meta or {}
        self.listed_symbols = []
        self.symbol_names = OrderedSet()
        self.short_description = None
        self.render_subpages = True
        self.title = ''
        self.meta = Schema(Page.meta_schema).validate({})
        self.__update_meta(meta)
        self.__discover_title(meta)
        self.link = Link(pagename, self.title or name, ref)

    def __update_meta(self, meta):
        for key, value in meta.items():
            try:
                self.meta.update(Schema(Page.meta_schema).validate({
                    key.replace('_', '-').lower(): value}))
            except SchemaError as _:
                warn('invalid-page-metadata',
                     '%s: Invalid metadata: \n%s, discarding metadata' %
                     (self.source_file, str(_)))

        if not self.meta.get('extra'):
            self.meta['extra'] = defaultdict()

        self.title = meta.get('title', self.title)
        self.thumbnail = meta.get('thumbnail')
        self.listed_symbols = OrderedSet(meta.get('symbols') or self.symbol_names)
        self.private_symbols = OrderedSet(meta.get('private-symbols') or self.private_symbols)
        self.symbol_names = OrderedSet(meta.get('symbols') or self.symbol_names)
        self.short_description = meta.get('short-description', self.short_description)
        self.render_subpages = meta.get('render-subpages', self.render_subpages)

    def __repr__(self):
        return "<Page %s>" % self.source_file

    @staticmethod
    def __get_empty_typed_symbols():
        typed_symbols_list = namedtuple(
            'TypedSymbolsList', ['name', 'symbols'])
        empty_typed_symbols = {}

        for subclass in all_subclasses(Symbol):
            empty_typed_symbols[subclass] = typed_symbols_list(
                subclass.get_plural_name(), [])

        return empty_typed_symbols

    def set_comment(self, comment):
        """
        Sets @comment as main comment for @self.
        """
        if comment:
            self.__update_meta(comment.meta)

        self.comment = comment

    def resolve_symbols(self, tree, database, link_resolver):
        """
        When this method is called, the page's symbol names are queried
        from `database`, and added to lists of actual symbols, sorted
        by symbol class.
        """
        self.typed_symbols = self.__get_empty_typed_symbols()
        all_syms = OrderedSet()
        for sym_name in self.symbol_names:
            sym = database.get_symbol(sym_name)
            self.__query_extra_symbols(
                sym, all_syms, tree, link_resolver, database)

        if tree.project.is_toplevel:
            page_path = self.link.ref
        else:
            page_path = self.project_name + '/' + self.link.ref

        if self.meta.get("auto-sort", True):
            all_syms = sorted(all_syms, key=lambda x: x.unique_name)
        for sym in all_syms:
            sym.update_children_comments()
            self.__resolve_symbol(sym, link_resolver, page_path)
            self.symbol_names.add(sym.unique_name)

        # Always put symbols with no parent at the end
        no_parent_syms = self.by_parent_symbols.pop(None, None)
        if no_parent_syms:
            self.by_parent_symbols[None] = no_parent_syms

        for sym_type in [ClassSymbol, AliasSymbol, InterfaceSymbol,
                         StructSymbol]:
            syms = self.typed_symbols[sym_type].symbols

            if not syms:
                continue

            if self.title is None:
                self.title = syms[0].display_name
            if self.comment is None:
                self.comment = Comment(name=self.source_file)
                self.comment.short_description = syms[
                    0].comment.short_description
                self.comment.title = syms[0].comment.title
            break

    # pylint: disable=no-self-use
    def __fetch_comment(self, sym, database):
        sym.comment = database.get_comment(sym.unique_name) or Comment(sym.unique_name)

    def __format_page_comment(self, formatter, link_resolver):
        if not self.comment:
            return

        if self.comment.short_description:
            self.short_description = formatter.format_comment(
                self.comment.short_description, link_resolver).strip()
            if self.short_description.startswith('<p>'):
                self.short_description = self.short_description[3:-4]
        if self.comment.title:
            self.title = formatter.format_comment(
                self.comment.title, link_resolver).strip()
            if self.title.startswith('<p>'):
                self.title = self.title[3:-4]

        if self.title:
            self.formatted_contents += '<h1 id="%s-page">%s</h1>' % (
                id_from_text(self.title), self.title)

        self.formatted_contents += formatter.format_comment(
            self.comment, link_resolver)

    def format(self, formatter, link_resolver, output):
        """
        Banana banana
        """

        if not self.title and self.source_file:
            title = os.path.splitext(self.source_file)[0]
            self.title = os.path.basename(title).replace('-', ' ')

        self.formatted_contents = u''

        self.build_path = os.path.join(formatter.get_output_folder(self),
                                       self.link.ref)

        if self.ast:
            out, diags = cmark.ast_to_html(self.ast, link_resolver)
            for diag in diags:
                warn(
                    diag.code,
                    message=diag.message,
                    filename=self.source_file)

            self.formatted_contents += out

        if not self.formatted_contents:
            self.__format_page_comment(formatter, link_resolver)

        self.output_attrs = defaultdict(lambda: defaultdict(dict))
        formatter.prepare_page_attributes(self)
        self.__format_symbols(formatter, link_resolver)
        self.detailed_description =\
            formatter.format_page(self)[0]

        if output:
            formatter.cache_page(self)

    # pylint: disable=no-self-use
    def get_title(self):
        """
        Banana banana
        """
        return self.title or 'unnamed'

    def __discover_title(self, meta):
        if meta is not None and 'title' in meta:
            self.title = meta['title']
        elif self.ast:
            self.title = cmark.title_from_ast(self.ast)

    def __format_symbols(self, formatter, link_resolver):
        for symbol in self.symbols:
            if symbol is None:
                continue
            debug('Formatting symbol %s in page %s' % (
                symbol.unique_name, self.source_file), 'formatting')
            symbol.detailed_description = formatter.format_symbol(
                symbol, link_resolver)

    def __query_extra_symbols(self, sym, all_syms, tree, link_resolver,
                              database):
        if sym:
            self.__fetch_comment(sym, database)
            new_symbols = sum(tree.resolving_symbol_signal(self, sym),
                              [])
            all_syms.add(sym)

            for symbol in new_symbols:
                self.__query_extra_symbols(
                    symbol, all_syms, tree, link_resolver, database)

    def __resolve_symbol(self, symbol, link_resolver, page_path):
        symbol.resolve_links(link_resolver)

        symbol.link.ref = "%s#%s" % (page_path, symbol.unique_name)

        for link in symbol.get_extra_links():
            link.ref = "%s#%s" % (page_path, link.id_)

        tsl = self.typed_symbols.get(type(symbol))
        if tsl:
            tsl.symbols.append(symbol)

            by_parent_symbols = self.by_parent_symbols.get(symbol.parent_name)
            if not by_parent_symbols:
                by_parent_symbols = self.__get_empty_typed_symbols()
                parent_name = symbol.parent_name
                if parent_name is None:
                    parent_name = 'Others symbols'
                self.by_parent_symbols[symbol.parent_name] = by_parent_symbols
            by_parent_symbols.get(type(symbol)).symbols.append(symbol)

        self.symbols.append(symbol)

        debug('Resolved symbol %s to page %s' %
              (symbol.unique_name, self.link.ref), 'resolution')


# pylint: disable=too-many-instance-attributes
class Tree:
    "Banana banana"

    def __init__(self, project, app):
        "Banana banana"
        self.project = project
        self.app = app

        self.__all_pages = {}

        self.__placeholders = {}
        self.root = None
        self.__dep_map = project.dependency_map
        self.__fill_dep_map()

        cmark.hotdoc_to_ast(u'', self)
        self.__extensions = {}
        self.resolve_placeholder_signal = Signal(optimized=True)
        self.list_override_pages_signal = Signal(optimized=True)
        self.update_signal = Signal()
        self.resolving_symbol_signal = Signal()

    def __fill_dep_map(self):
        for page in list(self.__all_pages.values()):
            for sym_name in page.symbol_names:
                self.__dep_map[sym_name] = page

    # pylint: disable=no-self-use
    def parse_page(self, source_file):
        with io.open(source_file, 'r', encoding='utf-8') as _:
            contents = _.read()

        return self.page_from_raw_text(source_file, contents)

    def add_unordered_subpages(self, extension, ext_index, ext_pages):
        for smart_key, ext_page in ext_pages.items():
            pagename = extension.get_pagename(ext_page.source_file)
            self.__all_pages[pagename] = ext_page
            ext_index.subpages.add(pagename)

    def parse_sitemap2(self, sitemap, extensions):
        ext_level = -1
        extensions = {ext.argument_prefix: ext for ext in extensions.values()}
        ext_pages = {}
        ext_index = None
        extension = None

        sitemap_pages = sitemap.get_all_sources()
        self.__all_pages = {}

        for name, level in sitemap:
            page = None

            if level <= ext_level:
                self.add_unordered_subpages (extension, ext_index, ext_pages)
                extension = None
                ext_level = -1
                ext_pages = {}
                ext_index = None

            if extension:
                smart_key = extension.get_possible_path(name)
            else:
                smart_key = None

            if name.endswith('-index'):
                ext_name = name[:-6]
                extension = extensions.get(ext_name)
                if extension is None:
                    # print ("That is a problem")
                    continue
                ext_level = level
                ext_pages = extension.make_pages()
                page = ext_pages['%s-index' % ext_name]
                del ext_pages['%s-index' % ext_name]
                ext_index = page
            elif name in ext_pages:
                page = ext_pages[name]
                del ext_pages[name]
            elif smart_key in ext_pages:
                page = ext_pages[smart_key]
                del ext_pages[smart_key]
            else:
                source_file = find_file(name, self.project.include_paths)
                if source_file is None:
                    error(
                        'no-such-subpage',
                        'No markdown file found for %s' % name,
                        filename=sitemap.source_file)

                ext = os.path.splitext(name)[1]
                if ext == '.json':
                    self.project.add_subproject(name, source_file)
                    page = Page(name, None, '', self.project.sanitized_name)
                    page.generated = True
                else:
                    page = self.parse_page(source_file)

                page.extension_name = extension.extension_name if extension else 'core'

            self.__all_pages[name] = page
            subpages = sitemap_pages.get(name, [])
            page.subpages = OrderedSet(subpages) | page.subpages
            if not page.meta.get('auto-sort', False):
                page.pre_sorted = True

        if ext_index:
            self.add_unordered_subpages(extension, ext_index, ext_pages)

        self.root = self.__all_pages[sitemap.index_file]

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def __parse_pages(self, sitemap):
        source_files = []
        source_map = {}
        placeholders = []

        overrides = self.list_override_pages_signal(
            self, self.project.include_paths) or []

        for override in overrides:
            source_files.append(override.file)
            source_map[override.file] = override.source_file

        for i, fname in enumerate(sitemap.get_all_sources().keys()):
            resolved = self.resolve_placeholder_signal(
                self, fname, self.project.include_paths)
            if not resolved:
                source_file = find_file(fname, self.project.include_paths)
                source_files.append(source_file)
                if source_file is None:
                    error(
                        'no-such-subpage',
                        'No markdown file found for %s' % fname,
                        filename=sitemap.source_file,
                        lineno=i,
                        column=0)
                source_map[source_file] = fname
            else:
                if resolved.extension_name:
                    self.__placeholders[fname] = resolved.extension_name
                if resolved.source and not resolved.generation_source:
                    source_files.append(resolved.source)
                    source_map[resolved.source] = fname
                else:
                    if fname not in self.__all_pages:
                        source_path = resolved.source
                        source_name = fname
                        if resolved.generation_source:
                            source_name = resolved.generation_source
                        page = Page(source_path or source_name, None, '',
                                    self.project.sanitized_name)
                        page.generated = True
                        self.__all_pages[fname] = page
                        self.__all_pages[source_name] = page
                        placeholders.append(fname)

        for source_file in source_files:
            pagename = source_map[source_file]
            page = self.parse_page(source_file)
            self.__all_pages[pagename] = page

        def setup_subpages(pagenames, get_pagename):
            """Setup subpages for pages with names in @pagenames"""
            sitemap_pages = sitemap.get_all_sources()
            for pagename in pagenames:
                page = self.__all_pages[get_pagename(pagename)]

                subpages = sitemap_pages.get(get_pagename(pagename), [])
                page.subpages = OrderedSet(subpages) | page.subpages
                for subpage_name in page.subpages:
                    subpage = self.__all_pages[subpage_name]
                    if not subpage.meta.get('auto-sort', False):
                        subpage.pre_sorted = True

        setup_subpages(source_files, lambda x: source_map[x])
        setup_subpages(placeholders, lambda x: x)

    def __update_sitemap(self, sitemap):
        # We need a mutable variable
        level_and_name = [-1, 'core']

        def _update_sitemap(name, _, level, __):
            if name in self.__placeholders:
                level_and_name[1] = self.__placeholders[name]
                level_and_name[0] = level
            elif level == level_and_name[0]:
                level_and_name[1] = 'core'
                level_and_name[0] = -1

            page = self.__all_pages.get(name)
            page.extension_name = level_and_name[1]

        sitemap.walk(_update_sitemap)

    # pylint: disable=no-self-use
    def __setup_folder(self, folder):
        if not os.path.exists(folder):
            os.makedirs(folder)

    def __get_link_cb(self, link_resolver, name):
        url_components = urlparse(name)

        page = self.__all_pages.get(url_components.path)
        if not page:
            return None

        ext = self.__extensions[page.extension_name]
        formatter = ext.formatter
        prefix = formatter.get_output_folder(page)
        ref = page.link.ref
        if url_components.fragment:
            ref += '#%s' % url_components.fragment
        return Link(os.path.join(prefix, ref), page.link.get_title(), None)

    def resolve(self, uri):
        """
        Banana banana
        """
        return resolve(uri, self.project.include_paths)

    def walk(self, parent=None):
        """Generator that yields pages in infix order

        Args:
            parent: hotdoc.core.tree.Page, optional, the page to start
                traversal from. If None, defaults to the root of the tree.

        Yields:
            hotdoc.core.tree.Page: the next page
        """
        if parent is None:
            yield self.root
            parent = self.root

        for cpage_name in parent.subpages:
            cpage = self.__all_pages[cpage_name]
            yield cpage
            for page in self.walk(parent=cpage):
                yield page

    def add_page(self, parent, pagename, page):
        """
        Banana banana
        """
        self.__all_pages[pagename] = page
        if parent:
            parent.subpages.add(pagename)

    def page_from_raw_text(self, source_file, contents):
        """
        Banana banana
        """
        raw_contents = contents

        meta = {}
        if contents.startswith('---\n'):
            split = contents.split('\n...\n', 1)
            if len(split) == 2:
                contents = split[1]
                try:
                    blocks = yaml.load_all(split[0])
                    for block in blocks:
                        if block:
                            meta.update(block)
                except ConstructorError as exception:
                    warn('invalid-page-metadata',
                         '%s: Invalid metadata: \n%s' % (source_file,
                                                         str(exception)))

        output_path = os.path.dirname(os.path.relpath(
            source_file, next(iter(self.project.include_paths))))

        ast = cmark.hotdoc_to_ast(contents, self)
        return Page(source_file, ast, output_path, self.project.sanitized_name,
                    meta=meta, raw_contents=raw_contents)

    def parse_sitemap(self, sitemap):
        """
        Banana banana
        """
        self.__parse_pages(sitemap)
        self.root = self.__all_pages[sitemap.index_file]
        self.__update_sitemap(sitemap)
        self.update_signal(self)

    def get_pages(self):
        """
        Banana banana
        """
        return self.__all_pages

    def __update_dep_map(self, page, symbols):
        for sym in symbols:
            if not isinstance(sym, Symbol):
                continue

            self.__dep_map[sym.unique_name] = page
            self.__update_dep_map(page, sym.get_children_symbols())

    def resolve_symbols(self, database, link_resolver, page=None):
        """Will call resolve_symbols on all the stale subpages of the tree.
        Args:
          page: hotdoc.core.tree.Page, the page to resolve symbols in,
          will recurse on potential subpages.
        """

        page = page or self.root

        if page.is_stale:
            if page.ast is None and not page.generated:
                with io.open(page.source_file, 'r', encoding='utf-8') as _:
                    page.ast = cmark.hotdoc_to_ast(_.read(), self)

            page.resolve_symbols(self, database, link_resolver)
            self.__update_dep_map(page, page.symbols)

        for pagename in page.subpages:
            cpage = self.__all_pages[pagename]
            self.resolve_symbols(database, link_resolver, page=cpage)

    def format_page(self, page, link_resolver, output, extensions):
        """
        Banana banana
        """
        info('formatting %s' % page.source_file, 'formatting')
        extension = extensions[page.extension_name]
        extension.format_page(page, link_resolver, output)

    def format(self, link_resolver, output, extensions):
        """Banana banana
        """
        info('Formatting documentation tree', 'formatting')
        self.__setup_folder(output)

        link_resolver.get_link_signal.connect(self.__get_link_cb)
        # Page.formatting_signal.connect(self.__formatting_page_cb)
        # Link.resolving_link_signal.connect(self.__link_referenced_cb)

        self.__extensions = extensions

        for page in self.walk():
            self.format_page(page, link_resolver, output, extensions)

        self.__extensions = None
        link_resolver.get_link_signal.disconnect(self.__get_link_cb)

    def write_out(self, output):
        """Banana banana
        """
        for page in self.walk():
            ext = self.project.extensions[page.extension_name]
            ext.write_out_page(output, page)
