# -*- coding: utf-8 -*-
#
# Copyright © 2015-2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015-2016 Collabora Ltd
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
Utilities and baseclasses for extensions
"""

import os
from collections import defaultdict

from hotdoc.core.file_includer import find_md_file
from hotdoc.core.symbols import Symbol
from hotdoc.core.doc_tree import DocTree, Page
from hotdoc.formatters.html_formatter import HtmlFormatter
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.loggable import debug, info, warn, error
from hotdoc.utils.utils import OrderedSet


# pylint: disable=too-few-public-methods
class ExtDependency(object):
    """
    Represents a dependency on another extension.

    If not satisfied, the extension will not be instantiated.

    See the `BaseExtension.get_dependencies` static method documentation
    for more information.

    Attributes:
        dependency_name: str, the name of the extension depended on.
        is_upstream: bool, if set to true hotdoc will arrange for
            the extension depended on to have its `BaseExtension.setup`
            implementation called first. Circular dependencies will
            generate an error.
    """

    def __init__(self, dependency_name, is_upstream=False):
        """
        Constructor for `BaseExtension`.

        Args:
            dependency_name: str, see `ExtDependency.dependency_name`
            is_upstream: bool, see `ExtDependency.is_upstream`
        """
        self.dependency_name = dependency_name
        self.is_upstream = is_upstream


class BaseExtension(Configurable):
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
    sources = set()
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

    def reset(self):
        """
        This function is only useful for testing purposes, at least
        for now.
        """
        self.__created_symbols = defaultdict(OrderedSet)
        self.__package_root = None

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

    def get_stale_files(self, all_files, prefix=None):
        """
        Shortcut function to `change_tracker.ChangeTracker.get_stale_files`
        for the tracker of this instance's `BaseExtension.doc_repo`

        Args:
            all_files: see `change_tracker.ChangeTracker.get_stale_files`
        """
        prefix = prefix or self.extension_name
        return self.doc_repo.change_tracker.get_stale_files(
            all_files,
            prefix)

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
        if sym and type(sym) != Symbol and sym.filename:
            # assert sym.filename is not None
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
        elif self.smart_index and override_path in self._get_all_sources():
            path = find_md_file('%s.markdown' % name, include_paths)
            return path or True, None
        return None

    def __update_doc_tree_cb(self, doc_tree, unlisted_sym_names):
        if not self.smart_index:
            return

        self.__find_package_root()
        index = self.__get_index_page(doc_tree)
        if index is None:
            return

        if not index.title:
            index.title = self._get_smart_index_title()

        for sym_name in unlisted_sym_names:
            sym = self.doc_repo.doc_database.get_symbol(sym_name)
            if sym and sym.filename in self._get_all_sources():
                self.__created_symbols[sym.filename].add(sym_name)

        user_pages = [p for p in doc_tree.walk(index) if not p.generated]
        user_symbols = self.__get_user_symbols(user_pages)

        for source_file, symbols in self.__created_symbols.items():
            gen_symbols = symbols - user_symbols
            self.__add_subpage(doc_tree, index, source_file, gen_symbols)
            doc_tree.stale_symbol_pages(symbols)

    def __find_package_root(self):
        if self.__package_root:
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
            page.generated = True
            page.comment = self.doc_repo.doc_database.get_comment(page_name)
            doc_tree.add_page(index, page_name, page)
        else:
            page.is_stale = True

        page.symbol_names |= symbols

    def __get_user_symbols(self, pages):
        symbols = set()
        for page in pages:
            symbols |= page.symbol_names
        return symbols

    def __get_rel_source_path(self, source_file):
        return os.path.relpath(source_file, self.__package_root)

    def _get_smart_index_title(self):
        return 'Reference Manual'

    def _get_all_sources(self):
        return self.sources

    def format_page(self, page, link_resolver, output):
        """
        Called by `doc_repo.DocRepo.format_page`, to leave full control
        to extensions over the formatting of the pages they are
        responsible of.

        Args:
            page: doc_tree.Page, the page to format.
            link_resolver: links.LinkResolver, object responsible
                for resolving links potentially mentioned in `page`
            output: str, path to the output directory.
        """
        formatter = self.get_formatter('html')
        if page.is_stale:
            debug('Formatting page %s' % page.link.ref, 'formatting')

            if output:
                actual_output = os.path.join(output,
                                             formatter.get_output_folder())
                if not os.path.exists(actual_output):
                    os.makedirs(actual_output)
            else:
                actual_output = None

            page.format(formatter, link_resolver, actual_output)
        else:
            debug('Not formatting page %s, up to date' % page.link.ref,
                  'formatting')
