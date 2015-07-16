# -*- coding: utf-8 -*-

from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.loader import FileLoader

from base_formatter import Formatter, LocalLink, ExternalLink
from yattag import Doc, indent

import uuid

INDENT_HTML = False

def do_indent (string):
    if INDENT_HTML:
        return indent (string, indent_text=True)
    return string

class Callable(object):
    def __init__(self, return_value, name, parameters):
        self.return_value = return_value
        self.name = name
        self.parameters = parameters

class HtmlFormatter (Formatter):
    def __init__(self, *args, **kwargs):
        Formatter.__init__(self, *args, **kwargs)
        self.__paragraph_opened = False

        # Used to decide whether to render a separator
        searchpath = ['templates']
        self.engine = Engine(
            loader=FileLoader(searchpath, encoding='UTF-8'),
            extensions=[CoreExtension()]
        )

    def __maybe_close_paragraph (self):
        if self.__paragraph_opened:
            self.__paragraph_opened = False
            return "</p>"
        return ""

    def _get_extension (self):
        return "html"

    def _priv_format_linked_symbol (self, symbol):
        template = self.engine.get_template('linked_symbol.html')
        if hasattr (symbol, 'qualifiers'):
            return template.render ({'qualifiers': symbol.qualifiers,
                                    'type': symbol.type_name,
                                    'indirection': symbol.indirection,
                                    'type_link': symbol.link,
                                    'name': symbol.argname,
                                    })
        return template.render ({'qualifiers': '',
                                 'type': symbol.type_name,
                                 'indirection': '',
                                 'type_link': symbol.link,
                                 'name': '',
                                 })

    def _priv_format_callable_prototype (self, return_value, function_name,
            parameters, is_pointer):
        template = self.engine.get_template('callable_prototype.html')
        param_offset = ' ' * (len (function_name) + 2)
        if is_pointer:
            param_offset += 3 * ' '
        callable_ = Callable (return_value, function_name, parameters)
        return template.render ({'callable': callable_,
                                 'param_offset': param_offset,
                                 'is_pointer': is_pointer,
                                })

    def _priv_format_type_prototype (self, directive, type_name, name):
        template = self.engine.get_template('type_prototype.html')
        return template.render ({'directive': directive,
                                 'type_name': type_name,
                                 'name': name,
                                })

    def _priv_format_macro_prototype (self, macro, is_callable):
        template = self.engine.get_template('macro_prototype.html')
        return template.render ({'macro': macro,
                                 'is_callable': is_callable,
                                })

    def _priv_format_parameter_detail (self, parameter_name, parameter_detail):
        template = self.engine.get_template('parameter_detail.html')
        return template.render ({'param_name': parameter_name,
                                 'param_detail': parameter_detail,
                                })

    def _priv_format_symbol_detail (self, name, symbol_type, linkname,
            prototype, doc, retval, param_docs):
        template = self.engine.get_template('symbol_detail.html')
        return template.render ({'name': name,
                                 'symbol_type': symbol_type,
                                 'linkname': linkname,
                                 'prototype': prototype,
                                 'doc': doc,
                                 'retval': retval,
                                 'param_docs': param_docs,
                                })

    def _priv_format_enum_detail (self, enum):
        template = self.engine.get_template('enum_detail.html')
        return template.render ({'enum': enum})

    def _priv_format_callable_summary (self, return_value, function_name,
            is_callable, is_pointer):
        template = self.engine.get_template('callable_summary.html')

        return template.render({'return_value': return_value,
                                'function_name': function_name,
                                'is_callable': is_callable,
                                'is_pointer': is_pointer,
                               })

    def _priv_format_type_summary (self, type_type, type_name): 
        template = self.engine.get_template('type_summary.html')

        return template.render({'type_type': type_type,
                                'type_name': type_name,
                               })

    def _priv_format_macro_summary (self, macro_link, is_callable):
        template = self.engine.get_template('macro_summary.html')

        return template.render({'macro': macro_link,
                                'is_callable': is_callable,
                               })

    def __format_callable (self, callable_, name, symbol_type, is_callable=True,
            is_pointer=False):
        return_value = self._priv_format_linked_symbol (callable_.return_value)
        callable_link = self._priv_format_linked_symbol (callable_)

        parameters = []
        param_docs = []

        for param in callable_.parameters:
            parameters.append (self._priv_format_linked_symbol(param))
            param_docs.append (self._priv_format_parameter_detail (param.argname,
                param.formatted_doc))
        prototype = self._priv_format_callable_prototype (return_value,
                callable_.type_name, parameters, is_pointer)
        detail = self._priv_format_symbol_detail (name, symbol_type,
                callable_.link.get_link().split('#')[-1], prototype,
                callable_.formatted_doc, callable_.return_value, param_docs)
        summary = self._priv_format_callable_summary (return_value, callable_link,
                is_callable, is_pointer)

        return detail, summary

    def _priv_format_function (self, func):
        return self.__format_callable (func, func.type_name, "method")

    def _priv_format_signal (self, signal):
        return self.__format_callable (signal,
                signal.type_name, "signal", is_callable=False)

    def _priv_format_vfunction (self, func):
        return self.__format_callable (func, func.type_name, "virtual function")

    def _priv_format_callback (self, func):
        return self.__format_callable (func, func.type_name, "callback", is_pointer=True)

    def _priv_format_type (self, directive, type_, member_type):
        type_type = self._priv_format_linked_symbol (type_.type_)
        type_name = self._priv_format_linked_symbol (type_)
        name = type_.type_name

        if directive:
            summary = self._priv_format_type_summary (directive, type_name)
        else:
            summary = self._priv_format_type_summary (type_type, type_name)

        prototype = self._priv_format_type_prototype (directive, type_type,
                type_.type_name)
        detail = self._priv_format_symbol_detail (name, member_type,
                type_.link.get_link().split('#')[-1], prototype,
                type_.formatted_doc, None, None)
        return detail, summary

    def _priv_format_property (self, prop):
        return self._priv_format_type (None, prop, "property")

    def _priv_format_alias (self, alias):
        return self._priv_format_type ("typedef", alias, "alias")

    def _priv_format_field (self, field):
        return self._priv_format_type (None, field, "field")

    def _priv_format_summary (self, summaries, summary_type):
        if not summaries:
            return None
        template = self.engine.get_template('summary.html')
        return template.render({'summary_type': summary_type,
                                'summaries': summaries
                            })

    def _priv_format_macro (self, macro, is_callable=False):
        macro_link = self._priv_format_linked_symbol (macro)
        summary = self._priv_format_macro_summary (macro_link, is_callable)
        param_docs = []

        if is_callable:
            for param in macro.parameters:
                param_docs.append (self._priv_format_parameter_detail (param.type_name,
                    param.formatted_doc))

        prototype = self._priv_format_macro_prototype (macro, is_callable)
        detail = self._priv_format_symbol_detail (macro.type_name, "macro",
                macro.link.get_link().split ('#')[-1],
                prototype, macro.formatted_doc, None, param_docs) 
        return detail, summary

    def _priv_format_constant (self, constant): 
        return self._priv_format_macro (constant)

    def _priv_format_enum (self, enum):
        enum_link = self._priv_format_linked_symbol (enum)
        summary = self._priv_format_type_summary ("enum", enum_link)
        enum.parameters = enum.members
        detail = self._priv_format_enum_detail (enum)
        return detail, summary

    def _priv_format_function_macro (self, macro):
        return self._priv_format_macro (macro, is_callable=True)

    def _fill_class_template_dict (self, klass, dict_, singular, plural, summary_name):
        details = []
        summaries = []
        for element in getattr (klass, "%s" % plural):
            detail, summary = getattr (self, "_priv_format_%s" % singular)(element)
            if detail:
                details.append (detail)
            if summary:
                summaries.append (summary)
        summary = self._priv_format_summary (summaries, summary_name)
        dict_["%s_summary" % plural] = summary
        dict_["%s_details" % plural] = details

    def _format_class (self, klass, aggregate):
        dict_ = {'klass': klass,
                'short_description': klass.get_short_description (),
                'instance_doc': klass.formatted_doc,
                'class_doc': klass.get_class_doc (),
                }

        for tup in [('function', 'functions', 'Functions'),
                    ('signal', 'signals', 'Signals'),
                    ('function_macro', 'function_macros', 'Function Macros'),
                    ('vfunction', 'vfunctions', 'Virtual Functions'),
                    ('property', 'properties', 'Properties'),
                    ('field', 'fields', 'Fields'),
                    ('constant', 'constants', 'Constants'),
                    ('enum', 'enums', 'Enumerations'),
                    ('callback', 'callbacks', 'Callbacks'),
                    ('alias', 'aliases', 'Aliases')]:
            self._fill_class_template_dict (klass, dict_, *tup)
        template = self.engine.get_template('class.html')

        return template.render(dict_)

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

    def _format_property (self, prop_name, link):
        doc, tag, text = Doc().tagtext()
        if link:
            href = link.get_link()
        else:
            href = ""
        with tag('a', href = href):
            with tag ('span', klass="type"):
                text(u'“%s”' % prop_name)
        return do_indent (doc.getvalue())

    def _format_signal (self, signal_name, link):
        doc, tag, text = Doc().tagtext()
        if link:
            href = link.get_link()
        else:
            href = ""
        with tag('a', href = href):
            with tag ('span', klass="type"):
                text(u'“%s”' % signal_name)
        return do_indent (doc.getvalue())

    def _format_enum_value (self, prop_name, link):
        doc, tag, text = Doc().tagtext()
        if link:
            href = link.get_link()
        else:
            href = ""

        with tag('a', href = href):
            with tag ('code'):
                text('%s' % prop_name)
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
        doc.asis ('<pre class="programlisting">')
        return do_indent (doc.getvalue())

    def _format_code_start_with_language (self, language):
        doc, tag, text = Doc().tagtext()
        if language == 'c':
            language = 'source-c'

        doc.asis ("<pre class=\"%s programlisting\">" % language)
        return do_indent (doc.getvalue())

    def _format_code_end (self):
        doc, tag, text = Doc().tagtext()
        doc.asis ('</pre>')
        return do_indent (doc.getvalue())
