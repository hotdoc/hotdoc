"""
Utilities and baseclasses for extensions
"""

import os

from hotdoc.core.gtk_doc_parser import GtkDocParser
from hotdoc.core.naive_index import NaiveIndexFormatter
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
        self.created_symbols = {}

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
            self.created_symbols[sym.unique_name] = sym

        return sym

    def create_naive_index(self):
        """
        Banana banana
        """
        directory = self.EXTENSION_NAME + "_gen_markdown_files"
        index_name = self.EXTENSION_NAME + "-index.markdown"
        NaiveIndexFormatter(self.created_symbols,
                            directory=directory,
                            index_name=index_name)
        return os.path.join(directory, index_name)
