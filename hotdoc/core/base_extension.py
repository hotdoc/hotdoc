from ..formatters.html.html_formatter import HtmlFormatter
from .gtk_doc_parser import GtkDocParser

class ExtDependency(object):
    def __init__(self, dependency_name, upstream=False):
        self.dependency_name = dependency_name
        self.upstream = upstream

class BaseExtension(object):
    def __init__(self, doc_tool, args):
        self.doc_tool = doc_tool
        self._formatters = {"html": HtmlFormatter(doc_tool, [])}
        self._doc_parser = GtkDocParser(doc_tool)
        self.stale_source_files = []

    @staticmethod
    def add_arguments (parser):
        pass

    def get_doc_parser (self):
        return self._doc_parser

    def get_formatter (self, output_format):
        return self._formatters.get (output_format)

    def setup (self):
        pass

    def get_source_files(self):
        return []

    def set_stale_source_files(self, stale):
        self.stale_source_files = stale

    @staticmethod
    def get_dependencies():
        return []
