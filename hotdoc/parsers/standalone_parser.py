# -*- coding: utf-8 -*-
#
# Copyright © 2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2016 Collabora Ltd
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

"""
Implement a parser for standalone markdown pages,
and for sitemap files.
"""

import io
import os
from collections import OrderedDict, defaultdict
import cPickle as pickle

from hotdoc.core.exceptions import HotdocSourceException
from hotdoc.core.file_includer import find_md_file
from hotdoc.utils.loggable import debug, info, warn, error, Logger
from hotdoc.core.symbols import Symbol
from hotdoc.parsers import cmark
from hotdoc.utils.utils import dedent, dequote, IndentError, OrderedSet
from hotdoc.utils.simple_signals import Signal
from hotdoc.utils.configurable import Configurable
from hotdoc.formatters.html_formatter import HtmlFormatter


class SitemapDuplicateError(HotdocSourceException):
    """
    Raised when the same file was listed multiple times in
    a sitemap file.
    """
    pass


class SitemapError(HotdocSourceException):
    """
    Generic sitemap error.
    """
    pass


Logger.register_error_code('bad-indent', IndentError, domain='sitemap')
Logger.register_error_code('sitemap-duplicate', SitemapDuplicateError,
                           domain='sitemap')
Logger.register_error_code('sitemap-error', SitemapError,
                           domain='sitemap')


# pylint: disable=too-few-public-methods
class StandaloneParser(object):
    """
    Banana banana
    """
    pass


class Sitemap(object):
    """
    Represents the desired hierarchy of the generated output.

    Attributes:
        index_file: str, the path to the index file.
    """
    def __init__(self, root, index_file):
        self.__root = root
        self.index_file = index_file
        self.__all_sources = None

    def walk(self, action):
        """
        Walk the hierarchy, applying action to each filename.

        Args:
            action: callable, the callable to invoke for each filename,
                will be invoked with the filename, the subfiles, and
                the level in the sitemap.
        """
        action(self.index_file, self.__root, 0)
        self.__do_walk(self.__root, 1, action)

    def _dump(self):
        self.walk(self.__dump_one)

    def get_all_sources(self):
        """
        Returns:
            OrderedDict: all source file names in the hierarchy, paired with
                the names of their subpages.
        """
        if self.__all_sources is None:
            self.__all_sources = OrderedDict()
            self.walk(self.__add_one)
        return self.__all_sources

    def get_subpages(self, source_file):
        """
        Args:
            str: name of the source file for which to retrieve subpages.
        Returns:
            OrderedDict: The subpages of `source_file`
        """
        return self.get_all_sources()[source_file]

    def __add_one(self, source_file, subpages, _):
        self.__all_sources[source_file] = subpages.keys()

    # pylint: disable=no-self-use
    def __dump_one(self, source_file, _, level):
        print level * '\t' + source_file

    def __do_walk(self, parent, level, action):
        for source_file, subpages in parent.items():
            action(source_file, subpages, level)
            self.__do_walk(subpages, level + 1, action)


class SitemapParser(object):
    """
    Implements parsing of sitemap files, to generate `Sitemap` objects.
    """
    # pylint: disable=too-many-locals
    # pylint: disable=no-self-use
    def parse(self, filename):
        """
        Parse a sitemap file.

        Args:
            filename: str, the path to the sitemap file.

        Returns:
            Sitemap: the generated sitemap.
        """
        with io.open(filename, 'r', encoding='utf-8') as _:
            lines = _.readlines()

        all_source_files = set()

        lineno = 0
        root = None
        index = None
        cur_level = -1
        parent_queue = []

        for line in lines:
            try:
                level, line = dedent(line)
            except IndentError as exc:
                error('bad-indent', 'Invalid indentation', filename=filename,
                      lineno=lineno, column=exc.column)

            if not line:
                continue

            source_file = dequote(line)

            if not source_file:
                continue

            if source_file in all_source_files:
                error('sitemap-duplicate', 'Filename listed twice',
                      filename=filename, lineno=lineno, column=level * 8 + 1)

            all_source_files.add(source_file)

            page = OrderedDict()

            if root is not None and level == 0:
                error('sitemap-error', 'Sitemaps only support one root',
                      filename=filename, lineno=lineno, column=0)

            if root is None:
                root = page
                index = source_file
            else:
                lvl_diff = cur_level - level
                while lvl_diff >= 0:
                    parent_queue.pop()
                    lvl_diff -= 1

                parent_queue[-1][source_file] = page

            parent_queue.append(page)

            cur_level = level

            lineno += 1

        return Sitemap(root, index)


class Extension(Configurable):
    """
    All extensions should inherit from this base class

    Attributes:
        extension_name: str, the unique name of this extension, should
            be overriden and namespaced appropriately.
        doc_repo: doc_repo.DocRepo, the DocRepo instance which documentation
            hotdoc is working on.
        formatters: dict, a mapping of format -> `base_formatter.Formatter`
            subclass instances.
    """
    # pylint: disable=unused-argument
    extension_name = "base-extension"
    argument_prefix = ''

    index = None
    sources = None
    paths_arguments = {}
    path_arguments = {}
    smart_index = False

    def __init__(self, doc_repo):
        """Constructor for `BaseExtension`.

        This should never get called directly.

        Args:
            doc_repo: The `doc_repo.DocRepo` instance which documentation
                is being generated.
        """
        self.doc_repo = doc_repo
        DocTree.resolve_placeholder_signal.connect(
            self.__resolve_placeholder_cb)
        DocTree.update_signal.connect(self.__update_doc_tree_cb)

        if not hasattr(self, 'formatters'):
            self.formatters = {"html": HtmlFormatter([])}

        self.__created_symbols = defaultdict(OrderedSet)
        self.__overriden_md = {}
        self.__package_root = None

    # pylint: disable=no-self-use
    def warn(self, code, message):
        """
        Shortcut function for `loggable.warn`

        Args:
            code: see `utils.loggable.warn`
            message: see `utils.loggable.warn`
        """
        warn(code, message)

    # pylint: disable=no-self-use
    def error(self, code, message):
        """
        Shortcut function for `utils.loggable.error`

        Args:
            code: see `utils.loggable.error`
            message: see `utils.loggable.error`
        """
        error(code, message)

    def debug(self, message, domain=None):
        """
        Shortcut function for `utils.loggable.debug`

        Args:
            message: see `utils.loggable.debug`
            domain: see `utils.loggable.debug`
        """
        if domain is None:
            domain = self.extension_name
        debug(message, domain)

    def info(self, message, domain=None):
        """
        Shortcut function for `utils.loggable.info`

        Args:
            message: see `utils.loggable.info`
            domain: see `utils.loggable.info`
        """
        if domain is None:
            domain = self.extension_name
        info(message, domain)

    def get_formatter(self, output_format):
        """
        Get the `base_formatter.Formatter` instance of this extension
        for a given output format.

        Args:
            output_format: str, the output format, for example `html`
        Returns:
            base_formatter.Formatter: the formatter for this format,
                or `None`.
        """
        return self.formatters.get(output_format)

    def setup(self):
        """
        Extension subclasses should implement this to scan whatever
        source files they have to scan, and connect to the various
        signals they have to connect to.

        Note that this will be called *after* the `doc_tree.DocTree`
        of this instance's `BaseExtension.doc_repo` has been fully
        constructed, but before its `doc_tree.DocTree.resolve_symbols`
        method has been called.
        """
        pass

    def get_stale_files(self, all_files):
        """
        Shortcut function to `change_tracker.ChangeTracker.get_stale_files`
        for the tracker of this instance's `BaseExtension.doc_repo`

        Args:
            all_files: see `change_tracker.ChangeTracker.get_stale_files`
        """
        return self.doc_repo.change_tracker.get_stale_files(
            all_files,
            self.extension_name)

    @staticmethod
    def get_dependencies():
        """
        Override this to return the list of extensions this extension
        depends on if needed.

        Returns:
            list: A list of `ExtDependency` instances.
        """
        return []

    @classmethod
    def parse_standard_config(cls, config):
        """
        Subclasses should call this in their
        `utils.configurable.Configurable.parse_config` implementation.

        Args:
            config: core.config.ConfigParser, the configuration holder.
        """
        prefix = cls.argument_prefix
        prefix += '_'
        cls.sources = config.get_sources(prefix)
        cls.index = config.get_index(prefix)
        cls.smart_index = bool(config.get('%s_smart_index' %
                                          cls.argument_prefix))

        for arg, dest in cls.paths_arguments.items():
            val = config.get_paths(arg)
            setattr(cls, dest, val)

        for arg, dest in cls.path_arguments.items():
            val = config.get_path(arg)
            setattr(cls, dest, val)

    @classmethod
    def add_index_argument(cls, group, prefix=None, smart=True):
        """
        Subclasses may call this to add an index argument.

        Args:
            group: arparse.ArgumentGroup, the extension argument group
            prefix: str, arguments have to be namespaced
            smart: bool, whether smart index generation should be exposed
                for this extension
        """
        prefix = prefix or cls.argument_prefix

        group.add_argument(
            '--%s-index' % prefix, action="store",
            dest="%s_index" % prefix,
            help=("Name of the %s root markdown file, can be None" % (
                cls.extension_name)))

        if smart:
            group.add_argument(
                '--%s-smart-index' % prefix, action="store_true",
                dest="%s_smart_index" % prefix,
                help="Smart symbols list generation in %s" % (
                    cls.extension_name))

    @classmethod
    def add_sources_argument(cls, group, allow_filters=True, prefix=None):
        """
        Subclasses may call this to add sources and source_filters arguments.

        Args:
            group: arparse.ArgumentGroup, the extension argument group
            allow_filters: bool,  Whether the extension wishes to expose a
                source_filters argument.
            prefix: str, arguments have to be namespaced.
        """
        prefix = prefix or cls.argument_prefix

        group.add_argument("--%s-sources" % prefix,
                           action="store", nargs="+",
                           dest="%s_sources" % prefix,
                           help="%s source files to parse" % prefix)

        if allow_filters:
            group.add_argument("--%s-source-filters" % prefix,
                               action="store", nargs="+",
                               dest="%s_source_filters" % prefix,
                               help="%s source files to ignore" % prefix)

    @classmethod
    def add_path_argument(cls, group, argname, dest=None, help_=None):
        """
        Subclasses may call this to expose a path argument.

        Args:
            group: arparse.ArgumentGroup, the extension argument group
            argname: str, the name of the argument, will be namespaced.
            dest: str, similar to the `dest` argument of
                `argparse.ArgumentParser.add_argument`, will be namespaced.
            help_: str, similar to the `help` argument of
                `argparse.ArgumentParser.add_argument`.
        """
        prefixed = '%s-%s' % (cls.argument_prefix, argname)
        if dest is None:
            dest = prefixed.replace('-', '_')
            final_dest = dest[len(cls.argument_prefix) + 1:]
        else:
            final_dest = dest
            dest = '%s_%s' % (cls.argument_prefix, dest)

        group.add_argument('--%s' % prefixed, action='store',
                           dest=dest, help=help_)
        cls.path_arguments[dest] = final_dest

    @classmethod
    def add_paths_argument(cls, group, argname, dest=None, help_=None):
        """
        Subclasses may call this to expose a paths argument.

        Args:
            group: arparse.ArgumentGroup, the extension argument group
            argname: str, the name of the argument, will be namespaced.
            dest: str, similar to the `dest` argument of
                `argparse.ArgumentParser.add_argument`, will be namespaced.
            help_: str, similar to the `help` argument of
                `argparse.ArgumentParser.add_argument`.
        """
        prefixed = '%s-%s' % (cls.argument_prefix, argname)
        if dest is None:
            dest = prefixed.replace('-', '_')
            final_dest = dest[len(cls.argument_prefix) + 1:]
        else:
            final_dest = dest
            dest = '%s_%s' % (cls.argument_prefix, dest)

        group.add_argument('--%s' % prefixed, action='store', nargs='+',
                           dest=dest, help=help_)
        cls.paths_arguments[dest] = final_dest

    def get_or_create_symbol(self, *args, **kwargs):
        """
        Extensions that discover and create instances of `symbols.Symbol`
        should do this through this method, as it will keep an index
        of these which can be used when generating a "naive index".

        See `doc_database.DocDatabase.get_or_create_symbol` for more
        information.

        Args:
            args: see `doc_database.DocDatabase.get_or_create_symbol`
            kwargs: see `doc_database.DocDatabase.get_or_create_symbol`

        Returns:
            symbols.Symbol: the created symbol, or `None`.
        """
        sym = self.doc_repo.doc_database.get_or_create_symbol(*args, **kwargs)

        # pylint: disable=unidiomatic-typecheck
        if sym and type(sym) != Symbol:
            assert sym.filename is not None
            self.__created_symbols[sym.filename].add(sym.unique_name)

        return sym

    def __resolve_placeholder_cb(self, doc_tree, name, include_paths):
        self.__find_package_root()

        override_path = os.path.join(self.__package_root, name)
        if name == '%s-index' % self.argument_prefix:
            if self.index:
                path = find_md_file(self.index, include_paths)
                assert path is not None
                return path, self.extension_name
            return True, self.extension_name
        elif override_path in self._get_all_sources():
            path = find_md_file('%s.markdown' % name, include_paths)
            print "resolved", name, path
            return path or True, None
        return None

    def __update_doc_tree_cb(self, doc_tree):
        self.__find_package_root()
        index = self.__get_index_page(doc_tree)
        if index is None:
            return

        user_pages = list(doc_tree.walk(index))
        user_symbols = self.__get_user_symbols(user_pages)

        for source_file, symbols in self.__created_symbols.items():
            symbols = symbols - user_symbols
            self.__add_subpage(doc_tree, index, source_file, symbols)

    def __find_package_root(self):
        if self.__package_root is not None:
            return

        commonprefix = os.path.commonprefix(self._get_all_sources())
        self.__package_root = os.path.dirname(commonprefix)

    def __get_index_page(self, doc_tree):
        placeholder = '%s-index' % self.argument_prefix
        return doc_tree.get_pages().get(placeholder)

    def __add_subpage(self, doc_tree, index, source_file, symbols):
        page_name = self.__get_rel_source_path(source_file)
        page = doc_tree.get_pages().get(page_name)

        if not page:
            page = Page(page_name, None)
            page.extension_name = self.extension_name
            doc_tree.add_page(index, page)

        page.symbol_names |= symbols

    def __get_user_symbols(self, pages):
        symbols = set()
        for page in pages:
            symbols |= page.symbol_names
        return symbols

    def __get_rel_source_path(self, source_file):
        return os.path.relpath(source_file, self.__package_root)

    def _get_languages(self):
        return []

    def _get_all_sources(self):
        return []


class Page(object):
    "Banana banana"

    def __init__(self, source_file, ast):
        "Banana banana"
        self.ast = ast
        self.extension_name = None
        self.source_file = source_file
        self.subpages = OrderedSet()
        if ast is not None:
            self.symbol_names = OrderedSet(cmark.symbol_names_in_ast(ast))
        else:
            self.symbol_names = OrderedSet()

    def __getstate__(self):
        return {'ast': None,
                'extension_name': self.extension_name,
                'source_file': self.source_file,
                'subpages': self.subpages,
                'symbol_names': self.symbol_names}


# pylint: disable=too-many-instance-attributes
class DocTree(object):
    "Banana banana"
    resolve_placeholder_signal = Signal(optimized=True)
    update_signal = Signal()

    def __init__(self, private_folder, include_paths):
        "Banana banana"
        self.__include_paths = include_paths
        self.__priv_dir = private_folder

        try:
            self.__all_pages = self.__load_private('pages.p')
            self.__incremental = True
        except IOError:
            self.__all_pages = {}

        self.__stale_pages = {}
        self.__placeholders = {}
        self.__root = None

    def __load_private(self, name):
        path = os.path.join(self.__priv_dir, name)
        return pickle.load(open(path, 'rb'))

    def __save_private(self, obj, name):
        path = os.path.join(self.__priv_dir, name)
        pickle.dump(obj, open(path, 'wb'))

    # pylint: disable=no-self-use
    def __parse_page(self, source_file):
        with io.open(source_file, 'r', encoding='utf-8') as _:
            contents = _.read()

        ast = cmark.hotdoc_to_ast(contents, None)
        return Page(source_file, ast)

    def __parse_pages(self, change_tracker, sitemap):
        source_files = []
        source_map = {}

        for fname in sitemap.get_all_sources().keys():
            resolved = self.resolve_placeholder_signal(
                self, fname, self.__include_paths)
            if resolved is None:
                source_file = find_md_file(fname, self.__include_paths)
                source_files.append(source_file)
                source_map[source_file] = fname
            else:
                resolved, ext_name = resolved
                if ext_name:
                    self.__placeholders[fname] = ext_name
                if resolved is not True:
                    source_files.append(resolved)
                    source_map[resolved] = fname

        stale, _ = change_tracker.get_stale_files(
            source_files, 'user-pages')

        stale_pages = {}

        for source_file in stale:
            stale_pages[source_map[source_file]] =\
                self.__parse_page(source_file)

        self.__stale_pages.update(stale_pages)
        self.__all_pages.update(stale_pages)

        for source_file in source_files:
            self.__all_pages[source_map[source_file]].subpages |=\
                sitemap.get_subpages(source_map[source_file])

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
            print name, page
            page.extension_name = level_and_name[1]

        sitemap.walk(_update_sitemap)
        self.update_signal(self)

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
            cpage = self.__all_pages[cpage_name]
            yield cpage
            for page in self.walk(parent=cpage):
                yield page

    def add_page(self, parent, page):
        """
        Banana banana
        """
        self.__all_pages[page.source_file] = page
        self.__stale_pages[page.source_file] = page
        parent.subpages.add(page.source_file)

    def parse_sitemap(self, change_tracker, sitemap):
        """
        Banana banana
        """
        self.__parse_pages(change_tracker, sitemap)
        self.__root = self.__all_pages[sitemap.index_file]
        self.__update_sitemap(sitemap)

    def get_stale_pages(self):
        """
        Banana banana
        """
        return self.__stale_pages

    def get_pages(self):
        """
        Banana banana
        """
        return self.__all_pages

    def persist(self):
        """
        Banana banana
        """
        self.__save_private(self.__all_pages, 'pages.p')
