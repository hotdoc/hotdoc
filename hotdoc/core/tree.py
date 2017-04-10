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
import pickle as pickle
from collections import namedtuple, defaultdict

# pylint: disable=import-error
import yaml
from yaml.constructor import ConstructorError
from schema import Schema, SchemaError, Optional, And

from hotdoc.core.inclusions import find_file, resolve
from hotdoc.core.symbols import Symbol, StructSymbol, ClassSymbol,\
    InterfaceSymbol, AliasSymbol
from hotdoc.core.links import Link
from hotdoc.core.filesystem import ChangeTracker
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


# pylint: disable=too-many-instance-attributes
class Page(object):
    "Banana banana"
    meta_schema = {Optional('title'): And(str, len),
                   Optional('symbols'): Schema([And(str, len)]),
                   Optional('short-description'): And(str, len),
                   Optional('render-subpages'): bool,
                   Optional('auto-sort'): bool,
                   Optional('full-width'): bool}

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
        self.typed_symbols = {}
        self.is_stale = True
        self.formatted_contents = None
        self.detailed_description = None
        self.build_path = None
        self.project_name = project_name
        self.cached_paths = OrderedSet()

        meta = meta or {}

        try:
            self.meta = Schema(Page.meta_schema).validate(meta)
        except SchemaError as _:
            warn('invalid-page-metadata',
                 '%s: Invalid metadata: \n%s' % (self.source_file,
                                                 str(_)))
            self.meta = meta

        self.symbol_names = OrderedSet(meta.get('symbols') or [])
        self.short_description = meta.get('short-description')
        self.render_subpages = meta.get('render-subpages', True)

        self.title = None
        self.__discover_title(meta)
        self.link = Link(pagename, self.title or name, ref)

    def __getstate__(self):
        return {'ast': None,
                'build_path': None,
                'title': self.title,
                'raw_contents': self.raw_contents,
                'short_description': self.short_description,
                'extension_name': self.extension_name,
                'link': self.link,
                'meta': self.meta,
                'source_file': self.source_file,
                'comment': self.comment,
                'generated': self.generated,
                'is_stale': False,
                'formatted_contents': None,
                'detailed_description': None,
                'output_attrs': None,
                'symbols': [],
                'typed_symbols': {},
                'subpages': self.subpages,
                'symbol_names': self.symbol_names,
                'project_name': self.project_name,
                'pre_sorted': self.pre_sorted,
                'cached_paths': self.cached_paths,
                'render_subpages': self.render_subpages}

    def resolve_symbols(self, tree, database, link_resolver):
        """
        When this method is called, the page's symbol names are queried
        from `database`, and added to lists of actual symbols, sorted
        by symbol class.
        """
        typed_symbols_list = namedtuple(
            'TypedSymbolsList', ['name', 'symbols'])

        for subclass in all_subclasses(Symbol):
            self.typed_symbols[subclass] = typed_symbols_list(
                subclass.get_plural_name(), [])

        all_syms = OrderedSet()
        for sym_name in self.symbol_names:
            sym = database.get_symbol(sym_name)
            self.__query_extra_symbols(
                sym, all_syms, tree, link_resolver, database)

        if tree.project.is_toplevel:
            page_path = self.link.ref
        else:
            page_path = self.project_name + '/' + self.link.ref

        for sym in all_syms:
            sym.update_children_comments()
            self.__resolve_symbol(sym, link_resolver, page_path)
            self.symbol_names.add(sym.unique_name)

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
        old_comment = sym.comment
        new_comment = database.get_comment(sym.unique_name)
        sym.comment = Comment(sym.unique_name)

        if new_comment:
            sym.comment = new_comment
        elif old_comment:
            if old_comment.filename not in (ChangeTracker.all_stale_files |
                                            ChangeTracker.all_unlisted_files):
                sym.comment = old_comment

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
            self.formatted_contents += '<h1>%s</h1>' % self.title

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
            symbol.skip = not formatter.format_symbol(symbol, link_resolver)

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
        self.symbols.append(symbol)

        debug('Resolved symbol %s to page %s' %
              (symbol.display_name, self.link.ref), 'resolution')


# pylint: disable=too-many-instance-attributes
class Tree(object):
    "Banana banana"

    def __init__(self, project, app):
        "Banana banana"
        self.project = project
        self.app = app

        if self.app.incremental:
            self.__all_pages = self.__load_private(
                'pages-%s.p' % self.project.sanitized_name)
        else:
            self.__all_pages = {}

        self.__placeholders = {}
        self.root = None
        self.__dep_map = self.__create_dep_map()

        cmark.hotdoc_to_ast(u'', self)
        self.__extensions = {}
        self.resolve_placeholder_signal = Signal(optimized=True)
        self.list_override_pages_signal = Signal(optimized=True)
        self.update_signal = Signal()
        self.resolving_symbol_signal = Signal()

    def __create_dep_map(self):
        dep_map = {}
        for page in list(self.__all_pages.values()):
            for sym_name in page.symbol_names:
                dep_map[sym_name] = page
        return dep_map

    def __load_private(self, name):
        path = os.path.join(self.project.get_private_folder(), name)
        with open(path, 'rb') as _:
            return pickle.loads(_.read())

    def __save_private(self, obj, name):
        path = os.path.join(self.project.get_private_folder(), name)
        with open(path, 'wb') as _:
            _.write(pickle.dumps(obj))

    # pylint: disable=no-self-use
    def __parse_page(self, source_file):
        with io.open(source_file, 'r', encoding='utf-8') as _:
            contents = _.read()

        return self.page_from_raw_text(source_file, contents)

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def __parse_pages(self, sitemap):
        change_tracker = self.app.change_tracker
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
            if resolved is None:
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
                resolved, ext_name = resolved
                if ext_name:
                    self.__placeholders[fname] = ext_name
                if resolved is not True:
                    source_files.append(resolved)
                    source_map[resolved] = fname
                else:
                    if fname not in self.__all_pages:
                        page = Page(fname, None, '',
                                    self.project.sanitized_name)
                        page.generated = True
                        self.__all_pages[fname] = page
                        placeholders.append(fname)

        stale, unlisted = change_tracker.get_stale_files(
            source_files, 'user-pages-%s' % self.project.sanitized_name)

        old_user_symbols = set()
        new_user_symbols = set()

        for source_file in stale:
            pagename = source_map[source_file]

            prev_page = self.__all_pages.get(pagename)
            if prev_page:
                old_user_symbols |= prev_page.symbol_names

            page = self.__parse_page(source_file)
            new_user_symbols |= page.symbol_names

            newly_listed_symbols = OrderedSet(page.symbol_names)
            if prev_page:
                newly_listed_symbols -= prev_page.symbol_names

            self.stale_symbol_pages(newly_listed_symbols, page)

            if prev_page:
                page.subpages |= prev_page.subpages

            self.__all_pages[pagename] = page

        unlisted_pagenames = set()

        for source_file in unlisted:
            prev_page = None
            rel_path = None

            for ipath in self.project.include_paths:
                rel_path = os.path.relpath(source_file, ipath)
                prev_page = self.__all_pages.get(rel_path)
                if prev_page:
                    break

            if not prev_page:
                continue

            old_user_symbols |= prev_page.symbol_names
            self.__all_pages.pop(rel_path)
            unlisted_pagenames.add(rel_path)

        def setup_subpages(pagenames, get_pagename):
            """Setup subpages for pages with names in @pagenames"""
            sitemap_pages = sitemap.get_all_sources()
            for pagename in pagenames:
                page = self.__all_pages[get_pagename(pagename)]

                subpages = sitemap_pages.get(get_pagename(pagename), [])
                page.subpages = OrderedSet(subpages) | page.subpages
                for subpage_name in page.subpages:
                    if subpage_name not in unlisted_pagenames:
                        subpage = self.__all_pages[subpage_name]
                        if not subpage.meta.get('auto-sort', False):
                            subpage.pre_sorted = True
                page.subpages -= unlisted_pagenames

        setup_subpages(source_files, lambda x: source_map[x])
        setup_subpages(placeholders, lambda x: x)

        return old_user_symbols - new_user_symbols

    def __update_sitemap(self, sitemap):
        # We need a mutable variable
        level_and_name = [-1, 'core']

        def _update_sitemap(name, _, level):
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

    def stale_comment_pages(self, comment):
        """
        Banana banana
        """
        page = self.__dep_map.get(comment.name)
        if page:
            page.is_stale = True

    def stale_symbol_pages(self, symbols, new_page=None):
        """
        Banana banana
        """
        for sym in symbols:
            page = self.__dep_map.get(sym)
            if page:
                page.is_stale = True
                if new_page and new_page.source_file != page.source_file:
                    page.symbol_names.remove(sym)

    def parse_sitemap(self, sitemap):
        """
        Banana banana
        """
        unlisted_symbols = self.__parse_pages(sitemap)
        self.root = self.__all_pages[sitemap.index_file]
        self.__update_sitemap(sitemap)
        self.update_signal(self, unlisted_symbols)

    def get_stale_pages(self):
        """
        Banana banana
        """
        stale = {}
        for pagename, page in list(self.__all_pages.items()):
            if page.is_stale:
                stale[pagename] = page
        return stale

    def get_pages(self):
        """
        Banana banana
        """
        return self.__all_pages

    def get_page_for_symbol(self, unique_name):
        """
        Banana banana
        """
        return self.__dep_map.get(unique_name)

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

    def persist(self):
        """
        Banana banana
        """
        self.__save_private(self.__all_pages, 'pages-%s.p' %
                            self.project.sanitized_name)
