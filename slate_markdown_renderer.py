from docmain import get_sorted_symbols_from_sections
from markdown_renderer import MarkdownRenderer

# Input format for https://github.com/tripit/slate
class SlateMarkdownRenderer (MarkdownRenderer):
    def _start_index (self, libname):
        out = ""
        out += self._render_line ("---")
        out += self._render_paragraph ("title: %s" % libname)
        out += self._render_line ("language_tabs:")
        out += self._render_paragraph ("  - c")
        out += self._render_line ("toc_footers:")
        out += self._render_paragraph ("""  - <a href='http://github.com/tripit/slate'>Documentation Powered by Slate</a>""")
        out += self._render_line ("includes:")

        return out

    def _end_index (self):
        out = ""
        out += self._render_line ("")
        out += self._render_line ("search: true")
        out += self._render_line ("---")
        return out

    def _render_index (self, filenames, sections):
        out = ""
        symbols = []
        get_sorted_symbols_from_sections (sections, symbols)
        for symbol in symbols:
            if symbol in filenames:
                out += self._render_line ("  - %s" % symbol)
        return out


