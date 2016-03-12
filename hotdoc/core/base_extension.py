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

"""
Utilities and baseclasses for extensions
"""

import os

from collections import defaultdict, OrderedDict

from hotdoc.core.wizard import HotdocWizard
from hotdoc.core.doc_tree import DocTree
from hotdoc.core.file_includer import find_md_file
from hotdoc.core.exceptions import BadInclusionException
from hotdoc.formatters.html_formatter import HtmlFormatter
from hotdoc.utils.utils import OrderedSet
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.loggable import debug, info, warn, error, Logger

Logger.register_error_code('smart-index-missing', BadInclusionException,
                           domain='base-extension')


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
        EXTENSION_NAME: str, the unique name of this extension, should
            be overriden and namespaced appropriately.
        doc_repo: doc_repo.DocRepo, the DocRepo instance which documentation
            hotdoc is working on.
        formatters: dict, a mapping of format -> `base_formatter.Formatter`
            subclass instances.
    """
    # pylint: disable=unused-argument
    EXTENSION_NAME = "base-extension"

    index = None

    def __init__(self, doc_repo):
        """Constructor for `BaseExtension`.

        This should never get called directly.

        Args:
            doc_repo: The `doc_repo.DocRepo` instance which documentation
                is being generated.
        """
        self.doc_repo = doc_repo

        if not hasattr(self, 'formatters'):
            self.formatters = {"html": HtmlFormatter([])}

        self.__created_symbols = defaultdict(OrderedSet)

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
            domain = self.EXTENSION_NAME
        debug(message, domain)

    def info(self, message, domain=None):
        """
        Shortcut function for `utils.loggable.info`

        Args:
            message: see `utils.loggable.info`
            domain: see `utils.loggable.info`
        """
        if domain is None:
            domain = self.EXTENSION_NAME
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

    def finalize(self):
        """
        This method will be called during the last phase of the generation
        process. The only action taken after this is to persist and close
        some resources, such as the `doc_repo.DocRepo.doc_database` of
        this instance's `BaseExtension.doc_repo`
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
            self.EXTENSION_NAME)

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
    def add_index_argument(cls, group, prefix, smart):
        """
        Subclasses may all this to add an index argument.

        Args:
            group: arparse.ArgumentGroup, the extension argument group
            prefix: str, arguments have to be namespaced
            smart: bool, whether smart index generation should be exposed
                for this extension
        """
        group.add_argument(
            '--%s-index' % prefix, action="store",
            dest="%s_index" % prefix,
            help=("Name of the %s root markdown file, can be None" % (
                cls.EXTENSION_NAME)),
            finalize_function=HotdocWizard.finalize_path)

        if smart:
            group.add_argument(
                '--%s-smart-index' % prefix, action="store_true",
                dest="%s_smart_index" % prefix,
                help="Smart symbols list generation in %s" % (
                    cls.EXTENSION_NAME))

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

        if sym:
            self.__created_symbols[sym.filename].add(sym.unique_name)

        return sym

    # pylint: disable=no-self-use
    def _get_naive_link_title(self, source_file):
        """
        When a "naive index" is generated by an extension, this class
        generates links between the "base index" and its subpages.

        One subpage is generated per code source file, for example
        if a source file named `my-foo-bar.c` contains documentable
        symbols, a subpage will be created for it, and the label
        of the link in the index will be `my-foo-bar`. Override this
        method to provide a custom label instead.

        Args:
            source_file: The name of the source file to provide a custom
                link label for, for example `/home/user/my-foo-bar.c`

        Returns:
            str: a custom label.
        """
        stripped = os.path.splitext(source_file)[0]
        title = os.path.basename(stripped)
        return title

    def _get_naive_page_description(self, source_file):
        """
        When a "naive index" is generated by an extension, this class
        will preface every subpage it creates for a given source file
        with a description, the default being simply the name of the
        source file, stripped of its extension.

        Override this method to provide a custom description instead.

        Args:
            source_file: The name of the source file to provide a custom
                description for, for example `/home/user/my-foo-bar.c`

        Returns:
            str: a custom description.
        """
        stripped = os.path.splitext(source_file)[0]
        title = os.path.basename(stripped)
        return '## %s\n\n' % title

    def _get_user_index_path(self):
        return None

    def _get_all_sources(self):
        return []

    def __get_naive_index_path(self):
        index_name = 'gen-' + self.EXTENSION_NAME + "-index.markdown"
        dirname = self.doc_repo.get_generated_doc_folder()
        return os.path.join(dirname, index_name)

    # pylint: disable=too-many-locals
    def create_naive_index(self, all_source_files):
        """
        This class can generate an index for the documentable symbols
        in a set of source files. To make use of this feature, subclasses
        should call on this method when the well known name they registered
        is encountered by the `DocRepo.doc_repo.doc_tree` of their instance's
        `BaseExtension.doc_repo`.

        This will generate a set of initially empty markdown files, which
        should be populated by calling `BaseExtension.update_naive_index`
        once symbols have been discovered and created through
        `BaseExtension.get_or_create_symbol`.

        Args:
            all_source_files: list, a list of paths, for example
                `[my_foo_bar.c]`.
            user_index: Path to a potential user index
        Returns: tuple, the arguments expected from a index handler.
        """
        user_index = self._get_user_index_path()
        index_path = self.__get_naive_index_path()
        epage = self.doc_repo.doc_tree.pages.get(index_path)

        user_index_is_stale = False
        subpages_changed = True

        if user_index:
            filename = find_md_file(user_index, self.doc_repo.include_paths)
            if filename is None:
                self.warn('smart-index-missing', "Unknown smart index %s" %
                          filename)
                return None

            stale, unlisted = self.doc_repo.change_tracker.get_stale_files(
                [filename], 'gen-index-' + self.EXTENSION_NAME)

            if stale or unlisted:
                user_index_is_stale = True

            with open(filename, 'r') as _:
                preamble = _.read()
        else:
            preamble = '## Generated API reference\n'

        gen_paths = OrderedDict()
        full_gen_paths = set()
        for source_file in sorted(all_source_files):
            link_title = self._get_naive_link_title(source_file)
            markdown_name = 'gen-' + link_title + '.markdown'
            gen_paths[link_title] = markdown_name
            full_gen_paths.add(
                os.path.join(self.doc_repo.get_generated_doc_folder(),
                             markdown_name))

        if epage:
            subpages_changed = (full_gen_paths != set(epage.subpages.keys()))

        if user_index_is_stale or subpages_changed:
            with open(index_path, 'w') as _:
                _.write(preamble + '\n')
                for link_title, markdown_name in gen_paths.items():
                    _.write('#### [%s](%s)\n' % (link_title, markdown_name))

        return index_path, '', self.EXTENSION_NAME

    def __make_gen_path(self, source_file):
        dirname = self.doc_repo.get_generated_doc_folder()
        link_title = self._get_naive_link_title(source_file)
        gen_path = 'gen-' + link_title + '.markdown'
        gen_path = os.path.join(dirname, gen_path)

        return gen_path

    def __create_symbols_list(self, source_file, symbols, user_file):
        gen_path = self.__make_gen_path(source_file)

        if user_file:
            with open(user_file, 'r') as _:
                preamble = _.read()
        else:
            preamble = self._get_naive_page_description(source_file)

        info("Generating symbols list for %s" % source_file)

        with open(gen_path, 'w') as _:
            _.write(preamble + '\n')
            for symbol in sorted(symbols):
                containing_pages =\
                    self.doc_repo.doc_tree.get_pages_for_symbol(symbol)
                if containing_pages and gen_path not in containing_pages:
                    debug("symbol %s is already contained elsewhere" % symbol)
                    continue
                # FIXME: more generic escaping
                debug("Adding symbol %s to page %s" % (symbol, source_file))
                unique_name = symbol.replace('_', r'\_')
                _.write('* [%s]()\n' % unique_name)

    # pylint: disable=too-many-locals
    def update_naive_index(self, smart=False):
        """
        This method can populate the pages generated by
        `BaseExtension.create_naive_index` with the symbols created through
        `BaseExtension.get_or_create_symbol`.

        In smart mode, this method will take existing markdown files into
        account, according to this logic:

        For all source files as returned by `BaseExtension._get_all_sources`
        (which must thus be implemented), we try to find a markdown file
        in the markdown include paths named similarly, if one is found
        its contents are prepended to the generated page.

        Args:
            smart: bool, take existing markdown files into account.
        """
        index_path = self.__get_naive_index_path()
        subtree = DocTree(self.doc_repo.include_paths,
                          self.doc_repo.get_private_folder())

        user_files = {}
        source_map = {}

        if smart:
            all_sources = self._get_all_sources()
            for source in all_sources:
                bname = os.path.basename(source)
                stripped = os.path.splitext(bname)[0]
                user_file = find_md_file(stripped + '.markdown',
                                         self.doc_repo.include_paths)
                if user_file:
                    user_files[source] = user_file
                    source_map[user_file] = source

        stale, unlisted = self.doc_repo.change_tracker.get_stale_files(
            user_files.values(), 'gen-' + self.EXTENSION_NAME)
        stale |= unlisted

        for source_file, symbols in self.__created_symbols.items():
            user_file = user_files.pop(source_file, None)
            self.__create_symbols_list(source_file, symbols, user_file)

            if user_file:
                try:
                    stale.remove(user_file)
                except IndexError:
                    pass

        for user_file in stale:
            source_file = source_map[user_file]
            gen_path = self.__make_gen_path(source_file)
            epage = self.doc_repo.doc_tree.pages[gen_path]
            self.__create_symbols_list(source_file, epage.symbol_names,
                                       user_file)

        subtree.build_tree(index_path,
                           extension_name=self.EXTENSION_NAME,
                           parent_tree=self.doc_repo.doc_tree)
        self.doc_repo.doc_tree.pages.update(subtree.pages)

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
            page.formatted_contents = \
                self.doc_repo.doc_tree.page_parser.format_page(
                    page, link_resolver, formatter)
            page.format(formatter, link_resolver, output)
        else:
            debug('Not formatting page %s, up to date' % page.link.ref,
                  'formatting')
