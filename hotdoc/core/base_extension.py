"""
Utilities and baseclasses for extensions
"""

import os

from collections import defaultdict

from hotdoc.core.doc_tree import DocTree
from hotdoc.formatters.html_formatter import HtmlFormatter
from hotdoc.utils.utils import OrderedSet


# pylint: disable=too-few-public-methods
class ExtDependency(object):
    """
    Banana banana
    """

    def __init__(self, dependency_name, upstream=False):
        self.dependency_name = dependency_name
        self.upstream = upstream


class BaseExtension(object):
    """
    All extensions should inherit from this base class
    """
    # pylint: disable=unused-argument
    EXTENSION_NAME = "base-extension"

    def __init__(self, doc_tool, config):
        self.doc_tool = doc_tool
        self._formatters = {"html": HtmlFormatter([])}
        self.stale_source_files = []
        self.created_symbols = defaultdict(OrderedSet)
        self.__naive_path = None

    @staticmethod
    def add_arguments(parser):
        """
        Subclasses should implement this if they need to get
        arguments from the command line.
        """
        pass

    def get_formatter(self, output_format):
        """
        Banana banana
        """
        return self._formatters.get(output_format)

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
        return self.doc_tool.change_tracker.get_stale_files(
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
        sym = self.doc_tool.doc_database.get_or_create_symbol(*args, **kwargs)

        if sym:
            self.created_symbols[sym.filename].add(sym)

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
        index_path = os.path.join(self.doc_tool.include_paths[0], index_name)

        with open(index_path, 'w') as _:
            _.write('## API reference\n\n')
            for source_file in all_source_files:
                link_title = self._get_naive_link_title(source_file)
                markdown_name = link_title + '.markdown'
                _.write('#### [%s](%s)\n' % (link_title, markdown_name))

        self.__naive_path = index_path
        return index_path, '', self.EXTENSION_NAME

    def update_naive_index(self):
        """
        Banana banana
        """
        subtree = DocTree(self.doc_tool.include_paths,
                          self.doc_tool.get_private_folder())
        for source_file, symbols in self.created_symbols.items():
            link_title = self._get_naive_link_title(source_file)
            markdown_path = link_title + '.markdown'
            markdown_path = os.path.join(self.doc_tool.include_paths[0],
                                         markdown_path)
            with open(markdown_path, 'w') as _:
                _.write(self._get_naive_page_description(link_title))
                for symbol in symbols:
                    _.write('* [%s]()\n' % symbol.unique_name)

        subtree.build_tree(self.__naive_path,
                           extension_name=self.EXTENSION_NAME)
        self.doc_tool.doc_tree.pages.update(subtree.pages)

    def format_page(self, page, link_resolver, output):
        """
        Banana banana
        """
        formatter = self.get_formatter('html')
        if page.is_stale:
            self.doc_tool.doc_tree.page_parser.rename_page_links(page,
                                                                 formatter,
                                                                 link_resolver)
            page.format(formatter, link_resolver, output)
