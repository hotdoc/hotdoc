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

from hotdoc.core.inclusions import find_file
from hotdoc.core.symbols import Symbol
from hotdoc.core.tree import Page, OverridePage
from hotdoc.core.formatter import Formatter
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.loggable import debug, info, warn, error
from hotdoc.utils.utils import OrderedSet


# pylint: disable=too-few-public-methods
class ExtDependency(object):
    """
    Represents a dependency on another extension.

    If not satisfied, the extension will not be instantiated.

    See the `Extension.get_dependencies` static method documentation
    for more information.

    Attributes:
        dependency_name: str, the name of the extension depended on.
        is_upstream: bool, if set to true hotdoc will arrange for
            the extension depended on to have its `Extension.setup`
            implementation called first. Circular dependencies will
            generate an error.
    """

    def __init__(self, dependency_name, is_upstream=False):
        """
        Constructor for `Extension`.

        Args:
            dependency_name: str, see `ExtDependency.dependency_name`
            is_upstream: bool, see `ExtDependency.is_upstream`
        """
        self.dependency_name = dependency_name
        self.is_upstream = is_upstream


# pylint: disable=too-many-instance-attributes
class Extension(Configurable):
    """
    All extensions should inherit from this base class

    Attributes:
        extension_name: str, the unique name of this extension, should
            be overriden and namespaced appropriately.
        project: project.Project, the Project instance which documentation
            hotdoc is working on.
        formatter: formatter.Formatter, may be subclassed.
        argument_prefix (str): Short name of this extension, used as a prefix
            to add to automatically generated command-line arguments.
    """
    # pylint: disable=unused-argument
    extension_name = "base-extension"
    argument_prefix = ''
    paths_arguments = {}
    path_arguments = {}

    def __init__(self, app, project):
        """Constructor for `Extension`.

        This should never get called directly.

        Args:
            project: The `project.Project` instance which documentation
                is being generated.
        """
        self.project = project
        self.app = app
        self.sources = set()
        self.index = None
        self.smart_index = False
        self._created_symbols = defaultdict(OrderedSet)
        self.__package_root = None
        self.__overriden_pages = []

        self.formatter = self._make_formatter()

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

    def reset(self):
        """
        This function is only useful for testing purposes, at least
        for now.
        """
        self._created_symbols = defaultdict(OrderedSet)
        self.__package_root = None

    def setup(self):
        """
        Extension subclasses should implement this to scan whatever
        source files they have to scan, and connect to the various
        signals they have to connect to.

        Note that this will be called *after* the `tree.Tree`
        of this instance's `Extension.project` has been fully
        constructed, but before its `tree.Tree.resolve_symbols`
        method has been called.
        """
        self.project.tree.resolve_placeholder_signal.connect(
            self.__resolve_placeholder_cb)
        self.project.tree.list_override_pages_signal.connect(
            self.__list_override_pages_cb)
        self.project.tree.update_signal.connect(self.__update_tree_cb)

    def get_stale_files(self, all_files, prefix=None):
        """
        Shortcut function to `change_tracker.ChangeTracker.get_stale_files`
        for the tracker of this instance's `Extension.project`

        Args:
            all_files: see `change_tracker.ChangeTracker.get_stale_files`
        """
        prefix = prefix or self.extension_name
        prefix += '-%s' % self.project.sanitized_name
        return self.app.change_tracker.get_stale_files(
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

    def parse_toplevel_config(self, config):
        """Parses and make use of the toplevel configuration."""
        self.formatter.parse_toplevel_config(config)

    def parse_config(self, config):
        """
        Override this, making sure to chain up first, if your extension adds
        its own custom command line arguments, or you want to do any further
        processing on the automatically added arguments.

        The default implementation will set attributes on the extension:
        - 'sources': a set of absolute paths to source files for this extension
        - 'index': absolute path to the index for this extension
        - 'smart_index': bool, depending on whether a smart index was enabled

        Additionally, it will set an attribute for each argument added with
        `Extension.add_path_argument` or `Extension.add_paths_argument`, with
        the extension's `Extension.argument_prefix` stripped, and dashes
        changed to underscores.

        Args:
            config: a `config.Config` instance
        """
        prefix = self.argument_prefix
        self.sources = config.get_sources(prefix)
        self.index = config.get_index(prefix)
        self.smart_index = bool(config.get('%s_smart_index' %
                                           self.argument_prefix))

        for arg, dest in list(self.paths_arguments.items()):
            val = config.get_paths(arg)
            setattr(self, dest, val)

        for arg, dest in list(self.path_arguments.items()):
            val = config.get_path(arg)
            setattr(self, dest, val)

        self.formatter.parse_config(config)

    @staticmethod
    def add_arguments(parser):
        """
        Subclasses may implement this method to add their own arguments to
        the hotdoc binary.

        In this function, you should add an argument group to the passed-in
        parser, corresponding to your extension.
        You can then add arguments to that argument group.

        Example::

            @staticmethod
            def add_arguments(parser):
                group = parser.add_argument_group('Chilidoc',
                    'Delicious Hotdoc extension')
                Chilidoc.add_sources_argument(group)
                group.add_argument('--chili-spicy', action='store_true',
                    help='Whether to add extra pepper')

        Args:
            parser (argparse.ArgumentParser): Main hotdoc argument parser
        """
        pass

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
                           dest="%s_sources" % prefix.replace('-', '_'),
                           help="%s source files to parse" % prefix)

        if allow_filters:
            group.add_argument("--%s-source-filters" % prefix,
                               action="store", nargs="+",
                               dest="%s_source_filters" % prefix.replace(
                                   '-', '_'),
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

        See `database.Database.get_or_create_symbol` for more
        information.

        Args:
            args: see `database.Database.get_or_create_symbol`
            kwargs: see `database.Database.get_or_create_symbol`

        Returns:
            symbols.Symbol: the created symbol, or `None`.
        """
        if not kwargs.get('project_name'):
            kwargs['project_name'] = self.project.project_name

        sym = self.app.database.get_or_create_symbol(*args, **kwargs)
        # pylint: disable=unidiomatic-typecheck
        smart_key = self._get_smart_key(sym)
        if sym and type(sym) != Symbol and smart_key:
            self._created_symbols[smart_key].add(sym.unique_name)

        return sym

    def _make_formatter(self):
        return Formatter(self, [])

    def __list_override_pages_cb(self, tree, include_paths):
        if not self.smart_index:
            return

        self.__find_package_root()
        for source in self._get_all_sources():
            source_rel = self.__get_rel_source_path(source)

            for ext in ['.md', '.markdown']:
                override = find_file(source_rel + ext, include_paths)
                if override:
                    self.__overriden_pages.append(OverridePage(source_rel,
                                                               override))
                    break

        return self.__overriden_pages

    def __resolve_placeholder_cb(self, tree, name, include_paths):
        return self._resolve_placeholder(tree, name, include_paths)

    def _resolve_placeholder(self, tree, name, include_paths):
        self.__find_package_root()

        override_path = os.path.join(self.__package_root, name)
        if name == '%s-index' % self.argument_prefix:
            if self.index:
                path = find_file(self.index, include_paths)
                if path is None:
                    self.error("invalid-config",
                               "Could not find index file %s" % self.index)
                return path, self.extension_name
            return True, self.extension_name
        elif self.smart_index and override_path in self._get_all_sources():
            path = find_file('%s.markdown' % name, include_paths)
            return path or True, None
        return None

    def __update_tree_cb(self, tree, unlisted_sym_names):
        if not self.smart_index:
            return

        self.__find_package_root()
        index = self.__get_index_page(tree)
        if index is None:
            return

        if not index.title:
            index.title = self._get_smart_index_title()

        for override in self.__overriden_pages:
            page = tree.get_pages()[override.source_file]
            page.extension_name = self.extension_name
            tree.add_page(index, override.source_file, page)

        for sym_name in unlisted_sym_names:
            sym = self.app.database.get_symbol(sym_name)
            if sym and sym.filename in self._get_all_sources():
                self._created_symbols[self._get_smart_key(sym)].add(sym_name)

        user_pages = [p for p in tree.walk(index) if not p.generated]
        user_symbols = self.__get_user_symbols(user_pages)

        for source_file, symbols in list(self._created_symbols.items()):
            gen_symbols = symbols - user_symbols
            if not gen_symbols:
                continue
            self.__add_subpage(tree, index, source_file, gen_symbols)
            tree.stale_symbol_pages(symbols)

    def __find_package_root(self):
        if self.__package_root:
            return

        commonprefix = os.path.commonprefix(list(self._get_all_sources()))
        self.__package_root = os.path.dirname(commonprefix)

    def __get_index_page(self, tree):
        placeholder = '%s-index' % self.argument_prefix
        return tree.get_pages().get(placeholder)

    def __add_subpage(self, tree, index, source_file, symbols):
        page_name = self.__get_rel_source_path(source_file)
        page = tree.get_pages().get(page_name)

        needs_comment = False
        if not page:
            page = Page(page_name, None, os.path.dirname(page_name),
                        tree.project.sanitized_name)
            page.extension_name = self.extension_name
            page.generated = True
            tree.add_page(index, page_name, page)
            needs_comment = True
        else:
            if not source_file.endswith(('.markdown', '.md')) and not \
                    page.comment:
                needs_comment = True
            page.is_stale = True

        if needs_comment:
            source_abs = os.path.abspath(source_file)
            if os.path.exists(source_abs):
                page.comment = self.app.database.get_comment(source_abs)
            else:
                page.comment = self.app.database.get_comment(page_name)

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

    def _get_smart_key(self, symbol):
        return symbol.filename

    def format_page(self, page, link_resolver, output):
        """
        Called by `project.Project.format_page`, to leave full control
        to extensions over the formatting of the pages they are
        responsible of.

        Args:
            page: tree.Page, the page to format.
            link_resolver: links.LinkResolver, object responsible
                for resolving links potentially mentioned in `page`
            output: str, path to the output directory.
        """
        if page.is_stale:
            debug('Formatting page %s' % page.link.ref, 'formatting')

            if output:
                actual_output = os.path.join(output,
                                             'html')
                if not os.path.exists(actual_output):
                    os.makedirs(actual_output)
            else:
                actual_output = None

            page.format(self.formatter, link_resolver, actual_output)
        else:
            debug('Not formatting page %s, up to date' % page.link.ref,
                  'formatting')

    def get_subpages_sorted(self, pages, page):
        """Get @page subpages sorted appropriately."""

        sorted_pages = []
        to_sort = []
        for page in page.subpages:
            # Do not resort subprojects even if they are
            # 'generated'.
            if pages[page].pre_sorted:
                sorted_pages.append(page)
            else:
                to_sort.append(page)

        return sorted_pages + sorted(
            to_sort, key=lambda p: pages[p].get_title().lower())
