"""
Utilities and baseclasses for extensions
"""

import os

from collections import defaultdict

from hotdoc.core.gtk_doc_parser import GtkDocParser
from hotdoc.core.doc_tree import DocTree
from hotdoc.formatters.html.html_formatter import HtmlFormatter


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

    def __init__(self, doc_tool, args):
        self.doc_tool = doc_tool
        self._formatters = {"html": HtmlFormatter(doc_tool, [])}
        self._doc_parser = GtkDocParser(doc_tool)
        self.stale_source_files = []
        self.created_symbols = defaultdict(set)
        self.__naive_path = None

    @staticmethod
    def add_arguments(parser):
        """
        Subclasses should implement this if they need to get
        arguments from the command line.
        """
        pass

    def get_doc_parser(self):
        """
        Banana banana
        """
        return self._doc_parser

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
        sym = self.doc_tool.get_or_create_symbol(*args, **kwargs)

        if sym:
            self.created_symbols[sym.filename].add(sym)

        return sym

    def create_naive_index(self, all_source_files):
        """
        Banana banana
        """
        index_name = self.EXTENSION_NAME + "-index.markdown"
        index_path = os.path.join(self.doc_tool.doc_tree.prefix, index_name)

        with open(index_path, 'w') as _:
            for source_file in all_source_files:
                stripped = os.path.splitext(source_file)[0]
                stripped = os.path.basename(stripped)
                markdown_name = stripped + '.markdown'
                _.write('#### [%s](%s)\n' % (stripped, markdown_name))

        self.__naive_path = index_path
        return index_path, '', self.EXTENSION_NAME

    def update_naive_index(self):
        """
        Banana banana
        """
        subtree = DocTree(self.doc_tool, self.doc_tool.doc_tree.prefix)
        for source_file, symbols in self.created_symbols.items():
            stripped = os.path.splitext(source_file)[0]
            stripped = os.path.basename(stripped)
            markdown_path = stripped + '.markdown'
            markdown_path = os.path.join(self.doc_tool.doc_tree.prefix,
                                         markdown_path)
            with open(markdown_path, 'w') as _:
                _.write('## %s\n\n' % stripped)
                for symbol in symbols:
                    _.write('* [%s]()\n' % symbol.unique_name)

        subtree.build_tree(self.__naive_path,
                           extension_name=self.EXTENSION_NAME)
        self.doc_tool.doc_tree.pages.update(subtree.pages)
