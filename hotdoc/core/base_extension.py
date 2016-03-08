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

from collections import defaultdict

from hotdoc.core.doc_tree import DocTree
from hotdoc.formatters.html_formatter import HtmlFormatter
from hotdoc.utils.utils import OrderedSet
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.loggable import debug, info, warn, error


# pylint: disable=too-few-public-methods
class ExtDependency(object):
    """
    Banana banana
    """

    def __init__(self, dependency_name, is_upstream=False):
        self.dependency_name = dependency_name
        self.is_upstream = is_upstream


class BaseExtension(Configurable):
    """
    All extensions should inherit from this base class
    """
    # pylint: disable=unused-argument
    EXTENSION_NAME = "base-extension"

    def __init__(self, doc_repo):
        self.doc_repo = doc_repo
        self.formatters = {"html": HtmlFormatter([])}
        self.__created_symbols = defaultdict(OrderedSet)
        self.__naive_path = None

    # pylint: disable=no-self-use
    def warn(self, code, message):
        """Shortcut function for `loggable.warn`"""
        warn(code, message)

    # pylint: disable=no-self-use
    def error(self, code, message):
        """Shortcut function for `loggable.error`"""
        error(code, message)

    def debug(self, message, domain=None):
        """Shortcut function for `loggable.debug`"""
        if domain is None:
            domain = self.EXTENSION_NAME
        debug(message, domain)

    def info(self, message, domain=None):
        """Shortcut function for `loggable.info`"""
        if domain is None:
            domain = self.EXTENSION_NAME
        info(message, domain)

    def get_formatter(self, output_format):
        """
        Banana banana
        """
        return self.formatters.get(output_format)

    def setup(self):
        """
        Banana banana
        """
        pass

    def finalize(self):
        """
        Banana banana
        """
        pass

    def get_stale_files(self, all_files):
        """
        Banana banana
        """
        return self.doc_repo.change_tracker.get_stale_files(
            all_files,
            self.EXTENSION_NAME)

    @staticmethod
    def get_dependencies():
        """
        Banana banana
        """
        return []

    def get_or_create_symbol(self, *args, **kwargs):
        """
        Banana banana
        """
        sym = self.doc_repo.doc_database.get_or_create_symbol(*args, **kwargs)

        if sym:
            self.__created_symbols[sym.filename].add(sym)

        return sym

    # pylint: disable=no-self-use
    def _get_naive_link_title(self, source_file):
        stripped = os.path.splitext(source_file)[0]
        title = os.path.basename(stripped)
        return title

    def _get_naive_page_description(self, link_title):
        return '## %s\n\n' % link_title

    def create_naive_index(self, all_source_files):
        """
        Banana banana
        """
        index_name = self.EXTENSION_NAME + "-index.markdown"
        dirname = self.doc_repo.get_generated_doc_folder()
        index_path = os.path.join(dirname, index_name)

        with open(index_path, 'w') as _:
            _.write('## API reference\n\n')
            for source_file in sorted(all_source_files):
                link_title = self._get_naive_link_title(source_file)
                markdown_name = link_title + '.markdown'
                _.write('#### [%s](%s)\n' % (link_title, markdown_name))

        self.__naive_path = index_path
        return index_path, '', self.EXTENSION_NAME

    def update_naive_index(self):
        """
        Banana banana
        """
        subtree = DocTree(self.doc_repo.include_paths,
                          self.doc_repo.get_private_folder())
        dirname = self.doc_repo.get_generated_doc_folder()
        for source_file, symbols in self.__created_symbols.items():
            link_title = self._get_naive_link_title(source_file)
            markdown_path = link_title + '.markdown'
            markdown_path = os.path.join(dirname,
                                         markdown_path)
            with open(markdown_path, 'w') as _:
                _.write(self._get_naive_page_description(link_title))
                for symbol in sorted(symbols, key=lambda s: s.unique_name):
                    # FIXME: more generic escaping
                    unique_name = symbol.unique_name.replace('_', r'\_')
                    _.write('* [%s]()\n' % unique_name)

        subtree.build_tree(self.__naive_path,
                           extension_name=self.EXTENSION_NAME)
        self.doc_repo.doc_tree.pages.update(subtree.pages)

    def format_page(self, page, link_resolver, output):
        """
        Banana banana
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
