from ..extensions.gi_raw_parser import GtkDocRawCommentParser
from ..utils.loggable import Loggable

class BaseExtension(Loggable):
    def __init__(self, args):
        Loggable.__init__(self)
        from ..formatters.html.html_formatter import HtmlFormatter
        from ..extensions.gtk_doc_parser import GtkDocParser
        from hotdoc.core.doc_tool import doc_tool
        self._formatters = {"html": HtmlFormatter([], doc_tool)}
        self._raw_parser = GtkDocRawCommentParser()
        self._doc_parser = GtkDocParser()

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

    def build_extra_symbols (self):
        pass
