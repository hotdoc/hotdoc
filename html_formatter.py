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
        self.__formatting_class = False
        self.__prototype_context = None
        self.__prototypes_type = None

        # Used to decide whether to render a separator
        self.__first_in_section = False
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

    def _format_linked_symbol (self, symbol):
        template = self.engine.get_template('linked_symbol.html')
        return template.render ({'qualifiers': symbol.qualifiers,
                                'type': symbol.type_name,
                                'indirection': symbol.indirection,
                                'type_link': symbol.link,
                                'name': symbol.argname,
                                })

    def _format_callable_prototype (self, return_value, function_name,
            parameters, is_pointer):
        template = self.engine.get_template('function_detail.html')
        param_offset = ' ' * (len (function_name) + 2)
        if is_pointer:
            param_offset += 3 * ' '
        callable_ = Callable (return_value, function_name, parameters)
        return template.render ({'callable': callable_,
                                 'param_offset': param_offset,
                                 'is_pointer': is_pointer,
                                })

    def _format_field_prototype (self, type_link, field_name):
        template = self.engine.get_template('field_prototype.html')
        return template.render ({'type_link': type_link,
                                 'field_name': field_name,
                                })

    def _format_constant_prototype (self, constant):
        template = self.engine.get_template('constant_prototype.html')
        return template.render ({'constant_name': constant.type_name,
                                 'constant_value': constant.value,
                                })

    def _format_function_macro_prototype (self, macro):
        template = self.engine.get_template('function_macro_prototype.html')
        return template.render ({'macro': macro,
                                })

    def _format_parameter_doc (self, parameter_name, parameter_doc):
        template = self.engine.get_template('parameter_doc.html')
        return template.render ({'param_name': parameter_name,
                                 'param_doc': parameter_doc,
                                })

    def _format_callable_detail (self, name, linkname, prototype, doc, param_docs):
        template = self.engine.get_template('callable_detail.html')
        return template.render ({'name': name,
                                 'linkname': linkname,
                                 'prototype': prototype,
                                 'doc': doc,
                                 'param_docs': param_docs,
                                })

    def _format_enum_detail (self, enum):
        template = self.engine.get_template('enum_detail.html')
        return template.render ({'enum': enum})

    def _format_alias_prototype (self, type_, alias_name):
        template = self.engine.get_template('alias_prototype.html')
        return template.render ({'type_name': type_,
                                 'alias_name': alias_name,
                                })

    def _format_callable_summary (self, return_value, function_name,
            is_callable, is_pointer):
        template = self.engine.get_template('function_summary.html')

        return template.render({'return_value': return_value,
                                'function_name': function_name,
                                'is_callable': is_callable,
                                'is_pointer': is_pointer,
                               })

    def _format_type_summary (self, type_type, type_name): 
        template = self.engine.get_template('type_summary.html')

        return template.render({'type_type': type_type,
                                'type_name': type_name,
                               })

    def _format_function_macro_summary (self, function_macro):
        template = self.engine.get_template('function_macro_summary.html')

        return template.render({'macro': function_macro,
                               })

    def __format_callable (self, callable_, title_string, is_callable=True,
            is_pointer=False):
        return_value = self._format_linked_symbol (callable_.return_value)
        callable_link = self._format_linked_symbol (callable_)

        parameters = []
        param_docs = []

        for param in callable_.parameters:
            parameters.append (self._format_linked_symbol(param))
            param_docs.append (self._format_parameter_doc (param.argname,
                param.formatted_doc))
        prototype = self._format_callable_prototype (return_value,
                callable_.type_name, parameters, is_pointer)
        detail = self._format_callable_detail (title_string,
                callable_.link.get_link().split('#')[-1], prototype,
                callable_.formatted_doc, param_docs)
        summary = self._format_callable_summary (return_value, callable_link,
                is_callable, is_pointer)

        return detail, summary

    def _format_function (self, func):
        return self.__format_callable (func, "The '%s' method" % func.type_name)

    def _format_signal (self, signal):
        return self.__format_callable (signal, "The '%s' signal" %
                signal.type_name, is_callable=False)

    def _format_vfunction (self, func):
        return self.__format_callable (func, "The '%s' virtual function" %
                func.type_name)

    def _format_callback (self, func):
        return self.__format_callable (func, "The '%s' callback" %
                func.type_name, is_pointer=True)

    def _format_member (self, prop, member_type):
        type_link = self._format_linked_symbol (prop.type_)
        prop_link = self._format_linked_symbol (prop)
        summary = self._format_type_summary (type_link, prop_link)
        prototype = unicode (self._format_field_prototype (type_link,
            prop.type_name))
        detail = self._format_callable_detail (u"The “%s” %s" %
                (prop.type_name, member_type),
                prop.link.get_link().split('#')[-1], prototype,
                prop.formatted_doc, None)
        return detail, summary

    def _format_property (self, prop):
        return self._format_member (prop, "property")

    def _format_alias (self, alias):
        type_link = self._format_linked_symbol (alias.type_)
        alias_link = self._format_linked_symbol (alias)
        summary = self._format_type_summary ("typedef", alias_link)
        prototype = self._format_alias_prototype (type_link, alias.type_name)
        detail = self._format_callable_detail (u"The “%s” alias" %
                alias.type_name, alias.link.get_link().split('#')[-1],
                prototype, alias.formatted_doc, None)
        return detail, summary

    def _format_field (self, field):
        return self._format_member (field, "field")

    def _format_summary (self, summaries, summary_type):
        if not summaries:
            return None
        template = self.engine.get_template('summary.html')
        return template.render({'summary_type': summary_type,
                                'summaries': summaries
                            })

    def _format_constant (self, constant):
        constant_link = self._format_linked_symbol (constant)
        summary = self._format_type_summary ("#define", constant_link)
        prototype = self._format_constant_prototype (constant)
        detail = self._format_callable_detail (u'The “%s” constant' %
                constant.type_name, constant.link.get_link().split ('#')[-1],
                prototype, constant.formatted_doc, None)
        return detail, summary

    def _format_enum (self, enum):
        enum_link = self._format_linked_symbol (enum)
        summary = self._format_type_summary ("enum", enum_link)
        detail = self._format_enum_detail (enum)
        return detail, summary

    def _format_function_macro (self, macro):
        macro_link = self._format_linked_symbol (macro)
        summary = self._format_function_macro_summary (macro_link)
        param_docs = []

        for param in macro.parameters:
            param_docs.append (self._format_parameter_doc (param.type_name,
                param.formatted_doc))

        prototype = self._format_function_macro_prototype (macro)
        detail = self._format_callable_detail (u'The “%s” macro' %
                macro.type_name, macro.link.get_link().split ('#')[-1],
                prototype, macro.formatted_doc, param_docs) 
        return detail, summary

    def _fill_class_template_dict (self, klass, dict_, singular, plural, summary_name):
        details = []
        summaries = []
        for element in getattr (klass, "%s" % plural):
            detail, summary = getattr (self, "_format_%s" % singular)(element)
            if detail:
                details.append (detail)
            if summary:
                summaries.append (summary)
        summary = self._format_summary (summaries, summary_name)
        dict_["%s_summary" % plural] = summary
        dict_["%s_details" % plural] = details

    def _format_class (self, klass, aggregate):
        dict_ = {'klass': klass,
                'short_description': klass.get_short_description (),
                'instance_doc': klass.formatted_doc,
                'class_doc': klass.class_doc,
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
