# -*- coding: utf-8 -*-

from base_formatter import Formatter, LocalLink, ExternalLink
from yattag import Doc, indent

import uuid

INDENT_HTML = False

def do_indent (string):
    if INDENT_HTML:
        return indent (string, indent_text=True)
    return string

class HtmlFormatter (Formatter):
    def __init__(self, *args, **kwargs):
        Formatter.__init__(self, *args, **kwargs)
        self.__paragraph_opened = False
        self.__formatting_class = False
        self.__prototype_context = None
        self.__prototypes_type = None

        # Used to decide whether to render a separator
        self.__first_in_section = False

    def __maybe_close_paragraph (self):
        if self.__paragraph_opened:
            self.__paragraph_opened = False
            return "</p>"
        return ""

    def _get_extension (self):
        return "html"

    def _start_page (self, to_be_aggregated):
        if to_be_aggregated:
            return ""

        doc, tag, text = Doc().tagtext()
        with tag ('head'):
            doc.asis ('<meta http-equiv="Content-Type" content="text/html; charset=utf-8">')
            with tag ('meta', content='text/html; charset=UTF-8'):
                pass
            with tag ('link', rel='stylesheet', href='../style.css',
                    type='text/css'):
                pass
        doc.asis ('<div class="refentry">')
        return do_indent (doc.getvalue())

    def _end_page (self, to_be_aggregated):
        if to_be_aggregated:
            return ""

        doc, tag, text = Doc().tagtext()
        doc.asis ('</div>')
        return do_indent (doc.getvalue())

    def _start_doc (self):
        doc, tag, text = Doc().tagtext()
        if self.__formatting_class:
            with tag('h2'):
                text ("Description")
        doc.asis ('<p>')
        self.__paragraph_opened = True
        return do_indent (doc.getvalue())

    def _end_doc (self):
        doc, tag, text = Doc().tagtext()
        doc.asis (self.__maybe_close_paragraph ())
        return do_indent (doc.getvalue())

    def _start_short_description (self):
        self.__paragraph_opened = True
        return "<p>"

    def _end_short_description (self):
        doc, tag, text = Doc().tagtext()
        doc.asis (self.__maybe_close_paragraph ())
        return do_indent (doc.getvalue())

    def _start_function (self, function_name, param_names):
        doc, tag, text = Doc().tagtext()
        doc.asis ('<div class="refsect2">')
        with tag('a', name=function_name):
            pass
        with tag('h3', klass = 'method'):
            with tag ('span', klass = 'entry', id = "%s" %
                    function_name):
                text ('%s ()' % function_name)
        return do_indent (doc.getvalue())

    def _start_signal (self, signal_name):
        doc, tag, text = Doc().tagtext()
        doc.asis ('<div class="refsect2">')
        with tag('a', name=signal_name):
            pass
        with tag('h3'):
            text ("The ")
            with tag ('code', klass='literal'):
                text (u'“%s” signal' % signal_name)
        return do_indent (doc.getvalue())

    def _end_function (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('</div>')
        return do_indent (doc.getvalue())

    def _start_class (self, class_name):
        self.__formatting_class = True
        doc, tag, text = Doc().tagtext()
        with tag('a', name=class_name):
            pass
        with tag('h1', klass = 'class'):
            text (class_name)
        return do_indent (doc.getvalue())

    def _end_class (self):
        self.__formatting_class = False
        return ""

    def _start_prototypes (self, type_):
        self.__prototypes_type = type_.rstrip('s').lower()
        doc, tag, text = Doc().tagtext()
        with tag('h2'):
            text (type_)
        doc.asis ('<div class="informaltable">')
        doc.asis ("<table>")
        with tag('colgroup'):
            with tag('col', klass='%ss_return' % self.__prototypes_type, width='150px'):
                pass
            with tag('col', klass='%ss_name' % self.__prototypes_type):
                pass
        
        self.__prototype_context = (doc, tag, text)
        return ""

    def __format_prototype_summary(self, prototype, is_callable):
        doc, tag, text = self.__prototype_context
        first = True
        with tag('tr'):
            with tag ('td', klass='%s_type' % self.__prototypes_type):
                if prototype.retval.link:
                    with tag ('a', klass='link',
                            title=prototype.retval.format_type(),
                            href=prototype.retval.link.get_link()):
                        with tag ('span', klass='returnvalue'):
                            text(prototype.retval.format_type())
                else:
                    with tag ('span', klass='returnvalue'):
                        text(prototype.retval.format_type())
                text (' %s' % '*' * prototype.retval.indirection_level)
            with tag ('td', klass='%s_name' % self.__prototypes_type):
                with tag ('a', klass='link', title=prototype.name,
                        href=prototype.link.get_link()):
                    text (prototype.name)
                if is_callable:
                    with tag ('span', klass='c_punctuation'):
                        text ("()")

        return ""

    def __format_full_prototype (self, prototype):
        doc, tag, text = Doc().tagtext()
        with tag ('pre', klass='programlisting'):
            if prototype.retval.link:
                with tag ('a',
                        href=prototype.retval.link.get_link()):
                    with tag ('span', klass='returnvalue'):
                        text(prototype.retval.format_type())
            else:
                with tag ('span', klass='returnvalue'):
                    text(prototype.retval.format_type())
            text ('*' * prototype.retval.indirection_level)

            text ('\n%s (' % prototype.name)
            first_param = True
            for param in prototype.params:
                if not first_param:
                    doc.asis (',\n%s' % (' ' * (len (prototype.name) + 2)))
                with tag ('em', klass='parameter'):
                    with tag ('code'):
                        if param.link:
                            with tag ('a',
                                    klass='link',
                                    title=param.type_,
                                    href=param.link.get_link()):
                                with tag ('span', klass='type'):
                                    text(param.type_)
                        else:
                            with tag ('span', klass='type'):
                                text(param.type_)
                        text (' %s' % ('*' * param.indirection_level))
                        text (param.argname)
                first_param = False
            text (')')

        ret = doc.getvalue ()
        return ret

    def _format_prototype(self, prototype, is_callable):
        if self.__prototype_context:
            return self.__format_prototype_summary (prototype, is_callable)
        return self.__format_full_prototype (prototype)

    def _end_prototypes(self):
        doc, tag, text = self.__prototype_context
        self.__prototype_context = None
        doc.asis ("</table>")
        doc.asis ("</div>")
        ret = do_indent (doc.getvalue())
        return ret

    def _start_parameters (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('<div class="refsect3">')
        with tag ('a', name=str(hex(uuid.getnode()))):
            pass
        with tag ('h4'):
            text ('Parameters')
        doc.asis ('<div class="informaltable">')
        doc.asis ('<table width="100%" border="0">')
        with tag ('colgroup'):
            with tag ('col', klass='parameters_name', width='150px'):
                pass
            with tag ('col', klass='parameters_description'):
                pass
        doc.asis ('<tbody>')
        return do_indent (doc.getvalue())

    def _end_parameters (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('</tbody>')
        doc.asis ('</table>')
        doc.asis ('</div>')
        doc.asis ('</div>')
        return do_indent (doc.getvalue())

    def _start_parameter (self, param_name):
        doc, tag, text = Doc().tagtext()
        doc.asis ('<tr>')
        with tag ('td', klass='parameter_name'):
            with tag ('p'):
                text (param_name)
        doc.asis ('<td class="parameter_description">')
        return do_indent (doc.getvalue())

    def _end_parameter (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('</td>')
        doc.asis ('</tr>')
        return do_indent (doc.getvalue())

    def _start_return_value (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('<div class="refsect3">')
        with tag ('a', name=str(hex(uuid.getnode()))):
            pass
        with tag ('h4'):
            text ('Returns')
        return do_indent (doc.getvalue())

    def _end_return_value (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('</div>')
        return do_indent (doc.getvalue())

    def _format_index (self, pages):
        doc, tag, text = Doc().tagtext()
        out = ""
        out += self._start_page (False)
        with tag('div', klass='toc'):
            for page in pages:
                with tag ('dt'):
                    with tag ('span', klass='refentrytitle'):
                        with tag ('a', href=page.link.get_link()):
                            text (page.ident)
                    with tag ('span', klass='refpurpose'):
                        doc.asis (u' — %s' % page.get_short_description())
        out += do_indent (doc.getvalue ())
        out += self._end_page (False)
        return out

    def _format_parameter (self, param_name):
        doc, tag, text = Doc().tagtext()
        with tag ('em', klass='parameter'):
            with tag ('code'):
                text (param_name)
        return do_indent (doc.getvalue())

    def _format_other (self, other):
        doc, tag, text = Doc().tagtext()
        text (other)
        return do_indent (doc.getvalue())

    def _format_note (self, other):
        doc, tag, text = Doc().tagtext()
        doc.asis (self.__maybe_close_paragraph ())
        with tag ('div', klass='admonition note'):
            with tag ('p'):
                text (other)
        return do_indent (doc.getvalue())

    def _format_new_line (self):
        return " "

    def _format_new_paragraph (self):
        doc, tag, text = Doc().tagtext()
        doc.asis (self.__maybe_close_paragraph ())
        doc.asis ("<p>")
        self.__paragraph_opened = True
        return do_indent (doc.getvalue())

    def _format_type_name (self, type_name, link):
        doc, tag, text = Doc().tagtext()
        if link:
            href = link.get_link()
        else:
            href = ""
        with tag('a', href=href):
            text(type_name)
        return do_indent (doc.getvalue())

    def _format_function_call (self, function_name, link):
        doc, tag, text = Doc().tagtext()
        if link:
            href = link.get_link()
        else:
            href = ""
        with tag('a', href = href):
            text(function_name)
        return do_indent (doc.getvalue())

    def _format_code_start (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('</pre>')
        return do_indent (doc.getvalue())

    def _format_code_start_with_language (self, language):
        doc, tag, text = Doc().tagtext()
        if language == 'c':
            language = 'source-c'

        doc.asis ("<pre class=\"%s\">" % language)
        return do_indent (doc.getvalue())

    def _format_code_end (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('</pre>')
        return do_indent (doc.getvalue())

    def _start_section (self, section_name):
        self.__first_in_section = True
        doc, tag, text = Doc().tagtext()
        doc.asis ('<div class="refsect1">')
        with tag ('h2'):
            text (section_name)
        return do_indent (doc.getvalue())

    def _end_section (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('</div>')
        return do_indent (doc.getvalue())

    def _start_section_block (self):
        if self.__first_in_section:
            self.__first_in_section = False
            return ""

        doc, tag, text = Doc().tagtext()
        with tag ('hr'):
            pass
        return do_indent (doc.getvalue())

