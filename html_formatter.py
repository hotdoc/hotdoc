from base_formatter import Formatter
from yattag import Doc

class HtmlFormatter (Formatter):
    def __init__(self, *args, **kwargs):
        Formatter.__init__(self, *args, **kwargs)
        self.__paragraph_opened = False
        self.__formatting_class = False

    def __maybe_close_paragraph (self):
        if self.__paragraph_opened:
            self.__paragraph_opened = False
            return "</p>"
        return ""

    def __format_title (self, title, level=1):
        return "<h%d>%s</h%d>" % (level, title, level)

    def _get_extension (self):
        return "html"

    def _start_page (self):
        if self.__paragraph_opened:
            print "wtf careful !"
        return "<section>"

    def _end_page (self):
        return "</section>"

    def _start_doc (self):
        if not self.__formatting_class:
            return ""

        doc, tag, text = Doc().tagtext()
        with tag('h2'):
            text ("Description")
        return doc.getvalue()

    def _start_short_description (self):
        self.__paragraph_opened = True
        return "<p>"

    def _end_short_description (self):
        return self.__maybe_close_paragraph ()

    def _start_function (self, function_name, param_names):
        doc, tag, text = Doc().tagtext()
        with tag('h2', klass = 'method'):
            with tag ('span', klass = 'entry', id = "%s" %
                    function_name):
                text (function_name)
        return doc.getvalue()

    def _start_class (self, class_name, prototypes):
        self.__formatting_class = True
        doc, tag, text = Doc().tagtext()
        with tag('h1', klass = 'class'):
            text (class_name)
        return doc.getvalue()

    def _end_class (self):
        self.__formatting_class = False
        return ""

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

    def _format_parameter (self, param_name):
        return "<strong>%s</strong>" % param_name

    def _format_other (self, other):
        doc, tag, text = Doc().tagtext()
        text (other)
        return doc.getvalue()

    def _format_note (self, other):
        out = ""
        out += self.__maybe_close_paragraph()
        doc, tag, text = Doc().tagtext()
        with tag ('div', klass='admonition note'):
            with tag ('p'):
                text (other)
        out += doc.getvalue()
        return out

    def _format_new_line (self):
        return " "

    def _format_new_paragraph (self):
        out = ""
        out += self.__maybe_close_paragraph ()
        out += "<p>"
        self.__paragraph_opened = True
        return out

    def _format_type_name (self, type_name):
        doc, tag, text = Doc().tagtext()
        with tag('a', href = type_name):
            text(type_name)
        return doc.getvalue()

    def _format_function_call (self, function_name):
        doc, tag, text = Doc().tagtext()
        with tag('a', href = function_name):
            text(function_name)
        return doc.getvalue()

    def _format_code_start (self):
        return "<pre>"

    def _format_code_start_with_language (self, language):
        if language == 'c':
            language = 'source-c'

        return "<pre class=\"%s\">" % language

    def _format_code_end (self):
        return "</pre>"
