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
from collections import OrderedDict

from hotdoc.core.symbols import Symbol
from hotdoc.core.tree import Page
from hotdoc.core.formatter import Formatter
from hotdoc.utils.configurable import Configurable
from hotdoc.core.exceptions import InvalidPageMetadata, InvalidOutputException
from hotdoc.utils.loggable import debug, info, warn, error, Logger
from hotdoc.utils.utils import OrderedSet, DefaultOrderedDict


class SymbolListedTwiceException(InvalidPageMetadata):
    pass


class InvalidRelocatedSourceException(InvalidPageMetadata):
    pass


Logger.register_warning_code(
    'unavailable-symbol-listed', InvalidOutputException, 'extension')
Logger.register_warning_code(
    'output-page-conflict', InvalidOutputException, 'extension')
Logger.register_warning_code(
    'symbol-listed-twice', SymbolListedTwiceException, 'extension')
Logger.register_warning_code(
    'invalid-relocated-source', InvalidRelocatedSourceException, 'extension')


# pylint: disable=too-few-public-methods
class ExtDependency:
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

    def __init__(self, dependency_name, is_upstream=False, optional=False):
        """
        Constructor for `Extension`.

        Args:
            dependency_name: str, see `ExtDependency.dependency_name`
            is_upstream: bool, see `ExtDependency.is_upstream`
        """
        self.dependency_name = dependency_name
        self.is_upstream = is_upstream
        self.optional = optional


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
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
    written_out_sitemaps = set()

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
        self.smart_sources = []
        self.index = None
        self.source_roots = OrderedSet()
        self._created_symbols = DefaultOrderedDict(OrderedSet)
        self.__package_root = None
        self.__toplevel_comments = OrderedSet()

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
        self._created_symbols = DefaultOrderedDict(OrderedSet)
        self.__package_root = None

    def get_pagename(self, name):
        self.__find_package_root()
        # Find the longest prefix
        longest = None
        for path in OrderedSet([self.__package_root]) | self.source_roots:
            commonprefix = os.path.commonprefix([path, name])
            if commonprefix == path and (longest is None or len(path) > len(longest)):
                longest = path

        if longest is not None:
            return os.path.relpath(name, longest)

        return name

    def get_symbol_page(self, symbol_name, symbol_pages, smart_pages, section_links):
        if symbol_name in symbol_pages:
            return symbol_pages[symbol_name]

        symbol = self.app.database.get_symbol(symbol_name)
        assert symbol is not None

        if symbol.parent_name and symbol.parent_name != symbol_name:
            page = self.get_symbol_page(
                symbol.parent_name, symbol_pages, smart_pages, section_links)
        else:
            smart_key = self._get_smart_key(symbol)
            if smart_key is None:
                return None

            if smart_key in smart_pages:
                page = smart_pages[smart_key]
            else:
                pagename = self.get_pagename(smart_key)
                page = Page(smart_key, True, self.project.sanitized_name, self.extension_name,
                            output_path=os.path.dirname(pagename))
                if page.link.ref in section_links:
                    self.warn('output-page-conflict',
                              'Creating a page for symbol %s would overwrite the page '
                              'declared in a toplevel comment (%s)' % (symbol_name, page.link.ref))
                    page = None
                else:
                    smart_pages[smart_key] = page

        if page is not None:
            symbol_pages[symbol_name] = page

        return page

    def _get_toplevel_comments(self):
        return self.__toplevel_comments

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def make_pages(self):
        # All symbol names that no longer need to be assigned to a page
        dispatched_symbol_names = set()

        # Map symbol names with pages
        # This is used for assigning symbols with a parent to the page
        # where their parent will be rendered, unless the symbol has been
        # explicitly assigned or ignored
        symbol_pages = {}

        smart_pages = OrderedDict()

        # Map pages with the sources they explicitly import
        imported_sources = {}

        # This is simply used as a conflict detection mechanism, see
        # hotdoc.core.tests.test_doc_tree.TestTree.test_section_and_path_conflict
        section_links = set()

        # These are used as a duplicate detection mechanism, map
        # relocated or ignored symbols to the source files where they were initially
        # listed
        relocated_symbols = {}
        private_symbols = {}

        # First we make one page per toplevel comment (eg. SECTION comment)
        # This is the highest priority mechanism for sorting symbols
        for comment in self._get_toplevel_comments():
            # Programming error from extension author
            assert comment.name
            symbol_names = comment.meta.pop('symbols', [])
            private_symbol_names = comment.meta.pop('private-symbols', [])
            sources = comment.meta.pop('sources', None)

            page = Page(comment.name, True, self.project.sanitized_name, self.extension_name,
                        comment=comment)

            for symbol_name in symbol_names:
                if symbol_name in relocated_symbols:
                    self.warn('symbol-listed-twice',
                              'Symbol %s listed in %s was already listed in %s' %
                              (symbol_name, comment.filename, relocated_symbols[symbol_name]))
                    continue
                elif symbol_name in private_symbols:
                    self.warn('symbol-listed-twice',
                              'Symbol %s listed in %s was marked as private in %s' %
                              (symbol_name, comment.filename, private_symbols[symbol_name]))
                    continue
                else:
                    page.symbol_names.add(symbol_name)
                    symbol_pages[symbol_name] = page
                    relocated_symbols[symbol_name] = comment.filename
                    dispatched_symbol_names.add(symbol_name)

            for symbol_name in private_symbol_names:
                if symbol_name in relocated_symbols:
                    self.warn('symbol-listed-twice',
                              'Symbol %s marked private in %s was already listed in %s' %
                              (symbol_name, comment.filename, relocated_symbols[symbol_name]))
                    continue
                elif symbol_name in private_symbols:
                    self.warn('symbol-listed-twice',
                              'Symbol %s marked as private in %s was '
                              'already marked as private in %s' %
                              (symbol_name, comment.filename, private_symbols[symbol_name]))
                    continue
                private_symbols[symbol_name] = comment.filename
                symbol_pages[symbol_name] = None
                dispatched_symbol_names.add(symbol_name)

            section_links.add(page.link.ref)
            smart_key = self._get_comment_smart_key(comment)
            if smart_key in smart_pages:
                smart_pages[comment.name] = page
            else:
                smart_pages[smart_key] = page

            if sources is not None:
                abs_sources = []
                for source in sources:
                    if os.path.isabs(source):
                        abs_sources.append(source)
                    else:
                        abs_sources.append(os.path.abspath(os.path.join(
                            os.path.dirname(comment.filename), source)))
                imported_sources[page] = abs_sources

        # Used as a duplicate detection mechanism
        relocated_sources = {}

        # We now browse all the pages with explicitly imported sources
        # Importing sources has a lower level of priority than importing
        # symbols, which is why we do that in a separate loop
        for page, sources in imported_sources.items():
            for source in sources:
                if source not in self._get_all_sources():
                    self.warn('invalid-relocated-source',
                              'Source %s does not exist but is relocated in %s' %
                              (source, page.name))
                    continue

                if source in relocated_sources:
                    self.warn('invalid-relocated-source',
                              'Source %s relocated in %s was already relocated in %s' %
                              (source, page.name, relocated_sources[source]))
                    continue

                if source in self._created_symbols:
                    symbol_names = OrderedSet(
                        self._created_symbols[source]) - dispatched_symbol_names
                    page.symbol_names |= symbol_names
                    dispatched_symbol_names |= symbol_names

                relocated_sources[source] = page.name

        # We now browse all the symbols we have created
        for _, symbol_names in self._created_symbols.items():
            for symbol_name in symbol_names:
                if symbol_name in dispatched_symbol_names:
                    continue

                page = self.get_symbol_page(
                    symbol_name, symbol_pages, smart_pages, section_links)

                # Can be None if creating a page to hold the symbol conflicts with
                # a page explicitly declared in a toplevel comment or a parent has been
                # marked as private
                if page is None:
                    continue

                page.symbol_names.add(symbol_name)
                dispatched_symbol_names.add(symbol_name)

        # Finally we make our index page
        if self.index:
            index_page = self.project.tree.parse_page(
                self.index, self.extension_name)
        else:
            index_page = Page('%s-index' % self.argument_prefix, True, self.project.sanitized_name,
                              self.extension_name)

        if not index_page.title:
            index_page.title = self._get_smart_index_title()

        smart_pages['%s-index' % self.argument_prefix] = index_page

        return smart_pages

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
        pass

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

        Additionally, it will set an attribute for each argument added with
        `Extension.add_path_argument` or `Extension.add_paths_argument`, with
        the extension's `Extension.argument_prefix` stripped, and dashes
        changed to underscores.

        Args:
            config: a `config.Config` instance
        """
        prefix = self.argument_prefix
        self.sources = config.get_sources(prefix)
        self.smart_sources = [
            self._get_smart_filename(s) for s in self.sources]
        self.index = config.get_index(prefix)
        self.source_roots = OrderedSet(
            config.get_paths('%s_source_roots' % prefix))

        for arg, dest in list(self.paths_arguments.items()):
            val = config.get_paths(arg)
            setattr(self, dest, val)

        for arg, dest in list(self.path_arguments.items()):
            val = config.get_path(arg)
            setattr(self, dest, val)

        self.formatter.parse_config(config)

    def add_attrs(self, symbol, **kwargs):
        """
        Helper for setting symbol extension attributes
        """
        for key, val in kwargs.items():
            symbol.add_extension_attribute(self.extension_name, key, val)

    def get_attr(self, symbol, attrname):
        """
        Helper for getting symbol extension attributes
        """
        return symbol.extension_attributes.get(self.extension_name, {}).get(
            attrname, None)

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
    def get_assets_licensing(cls):
        return {}

    @classmethod
    def add_index_argument(cls, group):
        """
        Subclasses may call this to add an index argument.

        Args:
            group: arparse.ArgumentGroup, the extension argument group
            prefix: str, arguments have to be namespaced
        """
        prefix = cls.argument_prefix

        group.add_argument(
            '--%s-index' % prefix, action="store",
            dest="%s_index" % prefix,
            help=("Name of the %s root markdown file, can be None" % (
                cls.extension_name)))

    @classmethod
    def add_sources_argument(cls, group, allow_filters=True, prefix=None, add_root_paths=False):
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

        if add_root_paths:
            group.add_argument("--%s-source-roots" % prefix,
                               action="store", nargs="+",
                               dest="%s_source_roots" % prefix.replace(
                                   '-', '_'),
                               help="%s source root directories allowing files "
                                    "to be referenced relatively to those" % prefix)

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

    def add_comment(self, comment):
        if comment.toplevel:
            self.__toplevel_comments.add(comment)
        else:
            self.app.database.add_comment(comment)

    def create_symbol(self, *args, **kwargs):
        """
        Extensions that discover and create instances of `symbols.Symbol`
        should do this through this method, as it will keep an index
        of these which can be used when generating a "naive index".

        See `database.Database.create_symbol` for more
        information.

        Args:
            args: see `database.Database.create_symbol`
            kwargs: see `database.Database.create_symbol`

        Returns:
            symbols.Symbol: the created symbol, or `None`.
        """
        if not kwargs.get('project_name'):
            kwargs['project_name'] = self.project.project_name

        sym = self.app.database.create_symbol(*args, **kwargs)
        if sym:
            # pylint: disable=unidiomatic-typecheck
            if type(sym) != Symbol:
                self._created_symbols[sym.filename].add(sym.unique_name)

        return sym

    def rename_symbol(self, unique_name, target):
        sym = self.app.database.rename_symbol(unique_name, target)
        # pylint: disable=unidiomatic-typecheck
        if sym and type(sym) != Symbol:
            self._created_symbols[sym.filename].remove(target)
            self._created_symbols[sym.filename].add(sym.unique_name)

    def _make_formatter(self):
        return Formatter(self)

    def get_possible_path(self, name):
        self.__find_package_root()

        for path in OrderedSet([self.__package_root]) | self.source_roots:
            possible_path = os.path.join(path, name)
            if possible_path in self._get_all_sources():
                return self._get_smart_filename(possible_path)
        return None

    def __find_package_root(self):
        if self.__package_root:
            return

        commonprefix = os.path.commonprefix(
            list(self._get_all_sources()) + list(self.source_roots))
        self.__package_root = os.path.dirname(commonprefix)

    def _get_smart_index_title(self):
        return 'Reference Manual'

    def _get_all_sources(self):
        return self.sources

    def _get_smart_key(self, symbol):
        return symbol.filename

    def _get_smart_filename(self, filename):
        return filename

    def _get_comment_smart_key(self, comment):
        return comment.filename

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
        debug('Formatting page %s' % page.link.ref, 'formatting')

        if output:
            actual_output = os.path.join(output,
                                         'html')
            if not os.path.exists(actual_output):
                os.makedirs(actual_output)
        else:
            actual_output = None

        page.format(self.formatter, link_resolver, actual_output)

    def write_out_sitemap(self, opath):
        """
        Banana banana
        """
        if opath not in self.written_out_sitemaps:
            Extension.formatted_sitemap = self.formatter.format_navigation(
                self.app.project)
            if Extension.formatted_sitemap:
                escaped_sitemap = Extension.formatted_sitemap.replace(
                    '\\', '\\\\').replace('"', '\\"').replace('\n', '')
                js_wrapper = 'sitemap_downloaded_cb("%s");' % escaped_sitemap
                with open(opath, 'w') as _:
                    _.write(js_wrapper)

        self.written_out_sitemaps.add(opath)

    # pylint: disable=too-many-locals
    def write_out_page(self, output, page):
        """
        Banana banana
        """
        subpages = OrderedDict({})
        all_pages = self.project.tree.get_pages()
        subpage_names = self.get_subpages_sorted(all_pages, page)
        for pagename in subpage_names:
            proj = self.project.subprojects.get(pagename)

            if not proj:
                cpage = all_pages[pagename]
                sub_formatter = self.project.extensions[
                    cpage.extension_name].formatter
            else:
                cpage = proj.tree.root
                sub_formatter = proj.extensions[cpage.extension_name].formatter

            subpage_link, _ = cpage.link.get_link(self.app.link_resolver)
            prefix = sub_formatter.get_output_folder(cpage)
            if prefix:
                subpage_link = '%s/%s' % (prefix, subpage_link)
            subpages[subpage_link] = cpage

        html_subpages = self.formatter.format_subpages(page, subpages)

        js_dir = os.path.join(output, 'html', 'assets', 'js')
        if not os.path.exists(js_dir):
            os.makedirs(js_dir)
        sm_path = os.path.join(js_dir, 'sitemap.js')
        self.write_out_sitemap(sm_path)

        self.formatter.write_out(page, html_subpages, output)

    def get_subpages_sorted(self, pages, page):
        """Get @page subpages sorted appropriately."""

        sorted_pages = []
        to_sort = []
        for subpage in page.subpages:
            # Do not resort subprojects even if they are
            # 'generated'.
            if pages[subpage].pre_sorted:
                sorted_pages.append(subpage)
            else:
                to_sort.append(subpage)

        return sorted_pages + sorted(
            to_sort, key=lambda p: pages[p].get_title().lower())
