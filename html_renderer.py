from docmain import Renderer
from yattag import Doc

class HtmlRenderer (Renderer):
    def __init__(self, transformer, include_dirs, sections,
            do_class_aggregation=True):
        Renderer.__init__(self, transformer, include_dirs, sections,
                do_class_aggregation=do_class_aggregation)
        self.__paragraph_opened = False

    def __maybe_close_paragraph (self):
        if self.__paragraph_opened:
            self.__paragraph_opened = False
            return "</p>"
        return ""

    def __render_title (self, title, level=1):
        return "<h%d>%s</h%d>" % (level, title, level)

    def _get_extension (self):
        return "html"

    def _start_page (self):
        if self.__paragraph_opened:
            print "wtf careful !"
        return "<section>"

    def _end_page (self):
        return "</section>"

    def _start_function (self, function_name, param_names):
        doc, tag, text = Doc().tagtext()
        with tag('h2', klass = 'method'):
            with tag ('span', klass = 'entry', id = "%s" %
                    function_name):
                text (function_name)
        return doc.getvalue()

    def _start_class (self, class_name):
        doc, tag, text = Doc().tagtext()
        with tag('h1', klass = 'class'):
            text (class_name)
        return doc.getvalue()

    def _start_parameters (self):
        return "<dl><dt>Parameters:</dt><ul>"

    def _end_parameters (self):
        return "</ul></dl>"

    def _start_parameter (self, param_name):
        return "<li><p><strong>%s: </strong>" % param_name

    def _end_parameter (self):
        return "</p></li>"

    def _end_doc (self):
        return self.__maybe_close_paragraph ()

    def _render_parameter (self, param_name):
        return "<strong>%s</strong>" % param_name

    def _render_other (self, other):
        doc, tag, text = Doc().tagtext()
        text (other)
        return doc.getvalue()

    def _render_note (self, other):
        out = ""
        out += self.__maybe_close_paragraph()
        doc, tag, text = Doc().tagtext()
        with tag ('div', klass='admonition note'):
            with tag ('p'):
                text (other)
        out += doc.getvalue()
        return out

    def _render_new_line (self):
        return " "

    def _render_new_paragraph (self):
        out = ""
        out += self.__maybe_close_paragraph ()
        out += "<p>"
        self.__paragraph_opened = True
        return out

    def _render_type_name (self, type_name):
        doc, tag, text = Doc().tagtext()
        with tag('a', href = type_name):
            text(type_name)
        return doc.getvalue()

    def _render_function_call (self, function_name):
        doc, tag, text = Doc().tagtext()
        with tag('a', href = function_name):
            text(function_name)
        return doc.getvalue()

    def _render_code_start (self):
        return "<pre>"

    def _render_code_start_with_language (self, language):
        if language == 'c':
            language = 'source-c'

        return "<pre class=\"%s\">" % language

    def _render_code_end (self):
        return "</pre>"
