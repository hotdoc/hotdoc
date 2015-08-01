from markdown_formatter import MarkdownFormatter

# Input format for https://github.com/tripit/slate
class SlateMarkdownFormatter (MarkdownFormatter):
    def _start_index (self, libname):
        out = ""
        out += self._format_line ("---")
        out += self._format_paragraph ("title: %s" % libname)
        out += self._format_line ("language_tabs:")
        out += self._format_paragraph ("  - c")
        out += self._format_line ("toc_footers:")
        out += self._format_paragraph ("""  - <a href='http://github.com/tripit/slate'>Documentation Powered by Slate</a>""")
        out += self._format_line ("includes:")

        return out

    def _end_index (self):
        out = ""
        out += self._format_line ("")
        out += self._format_line ("search: true")
        out += self._format_line ("---")
        return out

    def _format_index (self, filenames, sections):
        out = ""
        symbols = []
        get_sorted_symbols_from_sections (sections, symbols)
        for symbol in symbols:
            if symbol in filenames:
                out += self._format_line ("  - %s" % symbol)
        return out


