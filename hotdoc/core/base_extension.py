from ..extensions.gi_raw_parser import GtkDocRawCommentParser
from ..utils.loggable import Loggable

class BaseExtension(Loggable):
    def __init__(self, doc_tool, args):
        Loggable.__init__(self)
        from ..formatters.html.html_formatter import HtmlFormatter
        from ..extensions.gtk_doc_parser import GtkDocParser
        self.doc_tool = doc_tool
        self._formatters = {"html": HtmlFormatter(doc_tool, [])}
        self._raw_parser = GtkDocRawCommentParser()
        self._doc_parser = GtkDocParser()
        self.stale_source_files = []

    @staticmethod
    def add_arguments (parser):
        pass

    def get_raw_comment_parser (self):
        return self._raw_parser

    def get_doc_parser (self):
        return self._doc_parser

    def get_formatter (self, output_format):
        return self._formatters.get (output_format)

    def setup (self):
        pass

    def insert_well_known_name (self, name):
        return None

    def create_page_from_well_known_name(self, wkn):
        return None

    def get_index(self):
        return None

    def get_extra_symbols (self):
        return {}

    def get_comments(self):
        return {}

    def get_source_files(self):
        return []

    def set_stale_source_files(self, stale):
        self.stale_source_files = stale
