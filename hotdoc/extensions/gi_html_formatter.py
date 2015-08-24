import re, os
from hotdoc.core.doc_tool import doc_tool
from hotdoc.formatters.html.html_formatter import HtmlFormatter
from hotdoc.core.links import Link, ExternalLink

class PythonLink (Link):
    def __init__(self, link, title):
        Link.__init__(self)
        self.link = link
        self._title = title

    def get_link(self):
        return self.link


class GIHtmlFormatter(HtmlFormatter):
    def __init__(self, gi_extension):
        from hotdoc.extensions.gi_extension import (GIClassSymbol,
                GIPropertySymbol, GISignalSymbol)
        from hotdoc.core.symbols import FunctionMacroSymbol

        module_path = os.path.dirname(__file__)
        searchpath = [os.path.join(module_path, "templates")]
        self.__gi_extension = gi_extension
        HtmlFormatter.__init__(self, searchpath)
        self._symbol_formatters[GIClassSymbol] = self._format_class
        self._symbol_formatters[GIPropertySymbol] = self._format_gi_property
        self._summary_formatters[GIPropertySymbol] = self._format_gi_property_summary
        self._symbol_formatters[GISignalSymbol] = self._format_gi_signal
        self._summary_formatters[GISignalSymbol] = self._format_gi_signal_summary
        self._ordering.insert (2, GIPropertySymbol)
        self._ordering.insert (3, GISignalSymbol)
        self.python_fundamentals = self.__create_python_fundamentals()

    def __create_python_fundamentals(self):
        string_link = \
                PythonLink('https://docs.python.org/2.7/library/functions.html#str',
                    'str')
        boolean_link = \
                PythonLink('https://docs.python.org/2.7/library/functions.html#bool',
                        'bool')
        true_link = \
                PythonLink('https://docs.python.org/2/library/constants.html#True',
                    'True')
        false_link = \
                PythonLink('https://docs.python.org/2/library/constants.html#False',
                    'False')
        pointer_link = \
                PythonLink('https://docs.python.org/2.7/library/functions.html#object',
                    'object')
        integer_link = \
                PythonLink('https://docs.python.org/2/library/functions.html#int',
                        'int')
        float_link = \
                PythonLink('https://docs.python.org/2/library/functions.html#float',
                        'float')

        fundamentals = {
                'gchar': string_link,
                'gchar*': string_link,
                'char*': string_link,
                'guchar': string_link,
                'guchar*': string_link,
                'gchararray': string_link,
                'guint': integer_link,
                'glong': integer_link,
                'gulong': integer_link,
                'gint64': integer_link,
                'guint64': integer_link,
                'gfloat': float_link,
                'gdouble': float_link,
                'gboolean': boolean_link,
                'TRUE': true_link,
                'FALSE': false_link,
                'gpointer': pointer_link,
                'void*': pointer_link
                }
        return fundamentals

    def _format_parameter_symbol (self, parameter):
        template = self.engine.get_template('gi_parameter_detail.html')

        annotations = self.__gi_extension.get_annotations (parameter)
        if self.__gi_extension.language == 'python':
            if parameter.out:
                return (None, False)
            annotations = []

        return (template.render ({'name': parameter.argname,
                                 'detail': parameter.formatted_doc,
                                 'annotations': annotations,
                                }), False)

    def _format_return_value_symbol (self, return_value):
        if not return_value or not return_value.formatted_doc:
            return ('', False)

        template = self.engine.get_template('gi_return_value.html')

        out_parameters = []

        if self.__gi_extension.language == "c":
            annotations = self.__gi_extension.get_annotations (return_value)
        else:
            ptemplate = self.engine.get_template('gi_parameter_detail.html')
            annotations = []
            for param in return_value.out_parameters:
                out_parameters.append (ptemplate.render ({'name': None,
                    'detail': param.formatted_doc, 'annotations': []}))

        return (template.render ({'return_value': return_value,
                                  'annotations': annotations,
                                  'out_parameters': out_parameters}), False)

    def _format_callable_summary (self, return_value, function_name,
            is_callable, is_pointer, flags):
        if self.__gi_extension.language == "python":
            is_pointer = False
            return_value = None

        return HtmlFormatter._format_callable_summary (self, return_value,
                function_name, is_callable, is_pointer, flags)

    def _format_callable (self, callable_, callable_type, title,
            is_pointer=False, flags=False):

        callable_.throws = False
        if self.__gi_extension.language == "python":
            callable_.return_value.out_parameters = []
            if callable_.parameters:
                last_param = callable_.parameters[-1]
                last_param_name = ''.join (last_param._make_name().split())
                if last_param_name == "GError**":
                    callable_.parameters.pop()
                    callable_.throws = True
                for param in callable_.parameters:
                    annotations = self.__gi_extension.get_annotations (param)
                    if param.out:
                        callable_.return_value.out_parameters.append (param)

        return HtmlFormatter._format_callable (self, callable_, callable_type, title,
                is_pointer, flags)

    def _format_prototype (self, function, is_pointer, title):
        if self.__gi_extension.language == "python":
            python_params = []
            out_params = []
            retval = function.return_value
            for param in function.parameters:
                param.formatted_link = self._format_type_tokens(param.type_tokens)
                if param.detailed_description is not None:
                    python_params.append (param)
                else:
                    out_params.append (param)

            if retval:
                retval.formatted_link = self._format_type_tokens(retval.type_tokens)
                if retval.link.title == 'void':
                    retval = None

            template = self.engine.get_template('python_prototype.html')
            c_name = function._make_name()


            return template.render ({'return_value': retval,
                'function_name': function.link.title, 'parameters':
                python_params, 'c_name': c_name, 'throws': function.throws,
                'out_params': out_params})

        return HtmlFormatter._format_prototype (self, function,
            is_pointer, title)

    def _format_type_tokens (self, type_tokens):
        if self.__gi_extension.language == "python":
            actual_type = ''
            new_tokens = []
            for tok in type_tokens:
                if not tok in ['*', 'const ', 'restrict ', 'volatile ']:
                    new_tokens.append (tok)
                if not tok in ['const ', 'restrict ', 'volatile ']:
                    if isinstance (tok, Link):
                        actual_type += tok.title
                    else:
                        actual_type += tok

            python_link = self.python_fundamentals.get (actual_type)
            if python_link:
                type_tokens = [python_link]
            else:
                type_tokens = new_tokens

        return HtmlFormatter._format_type_tokens (self, type_tokens)

    def _format_gi_property_summary (self, prop):
        template = self.engine.get_template('property_summary.html')
        if self.__gi_extension.language == "python":
            property_type = None
        else:
            property_type = self._format_linked_symbol (prop.type_)

        prop_link = self._format_linked_symbol (prop)

        return template.render({'property_type': property_type,
                                'property_link': prop_link,
                                'flags': prop.flags,
                               })

    def _format_gi_signal_summary (self, signal):
        return self._format_callable_summary (
                self._format_linked_symbol (signal.return_value),
                self._format_linked_symbol (signal),
                True,
                False,
                signal.flags)

    def _format_compound_summary (self, compound):
        template = self.engine.get_template('python_compound_summary.html')
        link = self._format_linked_symbol (compound)
        return template.render({'compound': link})

    def _format_struct_summary (self, struct):
        return self._format_compound_summary (struct)

    def _format_enum_summary (self, enum):
        return self._format_compound_summary (enum)

    def _format_alias_summary (self, alias):
        return self._format_compound_summary (alias)

    def _format_gi_signal (self, signal):
        title = "%s_callback" % re.sub ('-', '_', signal.link.title)
        return self._format_callable (signal, "signal", title, flags=signal.flags)

    def _format_struct (self, struct):
        members_list = self._format_members_list (struct.members, 'Fields')

        template = self.engine.get_template ("python_compound.html")
        out = template.render ({"compound": struct,
                                "members_list": members_list})
        return (out, False)

    def _format_enum (self, enum):
        for member in enum.members:
            template = self.engine.get_template ("enum_member.html")
            member.detailed_description = template.render ({
                                    'link': member.link,
                                    'detail': member.formatted_doc,
                                    'value': str (member.enum_value)})

        members_list = self._format_members_list (enum.members, 'Members')
        template = self.engine.get_template ("python_compound.html")
        out = template.render ({"compound": enum,
                                "members_list": members_list})
        return (out, False)

    def _format_gi_property(self, prop):
        type_link = self._format_linked_symbol (prop.type_)
        template = self.engine.get_template('property_prototype.html')
        prototype = template.render ({'property_name': prop.link.title,
                                      'property_type': type_link})
        template = self.engine.get_template ('property.html')
        res = template.render ({'prototype': prototype,
                               'property': prop})
        return (res, False)

    def _get_style_sheet (self):
        if self.__gi_extension.language == 'python':
            return 'redstyle.css'
        return 'style.css'

    def _format_class (self, klass):
        if self.__gi_extension.language == 'python':
            doc_tool.page_parser.rename_labels(klass,
                    self.__gi_extension.python_names)
        return HtmlFormatter._format_class (self, klass)

    def format (self):
        for l in self.__gi_extension.languages:
            self.__gi_extension.setup_language (l)
            self._output = os.path.join (doc_tool.output, l)
            if not os.path.exists (self._output):
                os.mkdir (self._output)
            HtmlFormatter.format (self)
