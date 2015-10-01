import re, os
from hotdoc.formatters.html.html_formatter import HtmlFormatter
from hotdoc.core.links import Link
from hotdoc.core.symbols import *


class GIHtmlFormatter(HtmlFormatter):
    def __init__(self, gi_extension, doc_tool):
        module_path = os.path.dirname(__file__)
        searchpath = [os.path.join(module_path, "templates")]
        self.__gi_extension = gi_extension
        HtmlFormatter.__init__(self, searchpath, doc_tool)
        self.python_fundamentals = self.__create_python_fundamentals()
        self.javascript_fundamentals = self.__create_javascript_fundamentals()

    def __create_javascript_fundamentals(self):
        string_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/String',
                        'String', None)
        boolean_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Boolean',
                        'Boolean', None)
        pointer_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Object', 'Object',
                        None)
        true_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Boolean',
                        'true', None)
        false_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Boolean',
                        'false', None)
        number_link = \
                Link('https://developer.mozilla.org/en-US/docs/Glossary/Number',
                        'Number', None)
        null_link = \
                Link('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/null',
                        'null', None)

        fundamentals = {
                'gchararray': string_link,
                'gunichar': string_link,
                'utf8': string_link,
                'gchar': number_link,
                'guchar': number_link,
                'gint8': number_link,
                'guint8': number_link,
                'gint16': number_link,
                'guint16': number_link,
                'gint32': number_link,
                'guint32': number_link,
                'gint64': number_link,
                'guint64': number_link,
                'gshort': number_link,
                'gint': number_link,
                'guint': number_link,
                'glong': number_link,
                'gulong': number_link,
                'gsize': number_link,
                'gssize': number_link,
                'gintptr': number_link,
                'guintptr': number_link,
                'gfloat': number_link,
                'gdouble': number_link,
                'gboolean': number_link,
                'TRUE': true_link,
                'FALSE': false_link,
                'gpointer': pointer_link,
                'NULL': null_link,
                }
        return fundamentals

    def __create_python_fundamentals(self):
        string_link = \
                Link('https://docs.python.org/2.7/library/functions.html#str',
                    'str', None)
        boolean_link = \
                Link('https://docs.python.org/2.7/library/functions.html#bool',
                        'bool', None)
        true_link = \
                Link('https://docs.python.org/2/library/constants.html#True',
                    'True', None)
        false_link = \
               Link('https://docs.python.org/2/library/constants.html#False',
                    'False', None)
        pointer_link = \
                Link('https://docs.python.org/2.7/library/functions.html#object',
                    'object', None)
        integer_link = \
                Link('https://docs.python.org/2/library/functions.html#int',
                        'int', None)
        float_link = \
                Link('https://docs.python.org/2/library/functions.html#float',
                        'float', None)
        none_link = \
                Link('https://docs.python.org/2/library/constants.html#None',
                        'None', None)
        unicode_link = \
                Link('https://docs.python.org/2/library/functions.html#unicode',
                        'unicode', None)

        gtype_link = \
                Link('https://developer.gnome.org/gobject/stable/'
                        'gobject-Type-Information.html#GType',
                        'GObject.Type', None)

        gvariant_link = \
                Link('https://developer.gnome.org/glib/stable/glib-GVariant.html',
                        'GLib.Variant', None)

        fundamentals = {
                "none": none_link,
                "gpointer": pointer_link,
                "gconstpointer": pointer_link,
                "gboolean": boolean_link,
                "gint8": integer_link,
                "guint8": integer_link,
                "gint16": integer_link,
                "guint16": integer_link,
                "gint32": integer_link,
                "guint32": integer_link,
                "gchar": integer_link,
                "guchar": integer_link,
                "gshort": integer_link,
                "gushort": integer_link,
                "gint": integer_link,
                "guint": integer_link,
                "gfloat": float_link,
                "gdouble": float_link,
                "utf8": unicode_link,
                "gunichar": unicode_link,
                "filename": string_link,
                "gchararray": string_link,
                "GType": gtype_link,
                "GVariant": gvariant_link,
                "gsize": integer_link,
                "gssize": integer_link,
                "goffset": integer_link,
                "gintptr": integer_link,
                "guintptr": integer_link,
                "glong": integer_link,
                "gulong": integer_link,
                "gint64": integer_link,
                "guint64": integer_link,
                "long double": float_link,
                "long long": integer_link,
                "unsigned long long": integer_link,
                "TRUE": true_link,
                "FALSE": false_link,
                "NULL": none_link,
        }

        return fundamentals

    def _format_annotations (self, annotations):
        template = self.engine.get_template('gi_annotations.html')
        return template.render ({'annotations': annotations})

    def _format_flags (self, flags):
        template = self.engine.get_template('gi_flags.html')
        out = template.render ({'flags': flags})
        return out

    def _format_callable_summary (self, return_value, function_name,
            is_callable, is_pointer):
        if self.__gi_extension.language in ["python", "javascript"]:
            is_pointer = False
            return_value = None

        return HtmlFormatter._format_callable_summary (self, return_value,
                function_name, is_callable, is_pointer)

    def _format_type_tokens (self, type_tokens):
        if self.__gi_extension.language != 'c':
            new_tokens = []
            for tok in type_tokens:
                if tok not in ['*', 'const', 'restrict', 'volatile']:
                    new_tokens.append (tok)
            return HtmlFormatter._format_type_tokens (self, new_tokens)
        return HtmlFormatter._format_type_tokens (self, type_tokens)

    def _format_return_value_symbol (self, retval):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_return_value_symbol (self, retval)

        out_parameters = retval.get_extension_attribute ('gi-extension',
                'out_parameters')

        if out_parameters is None:
            return HtmlFormatter._format_return_value_symbol (self, retval)

        gi_name = retval.get_extension_attribute ('gi-extension',
                'gi_name')

        return_values = []

        if gi_name == 'none':
            retval = None
        else:
            retval.formatted_link = self._format_linked_symbol(retval)
            return_values.append (retval)

        for param in out_parameters:
            param.formatted_link = self._format_linked_symbol(param)
            return_values.append (param)

        if not return_values:
            return (False, None)

        template = self.engine.get_template ('multi_return_value.html')
        return (template.render ({'return_values': return_values}), False)

    def _format_parameter_symbol (self, parameter):
        if self.__gi_extension.language != 'c':
            direction = parameter.get_extension_attribute ('gi-extension',
                    'direction')
            if direction == 'out':
                return (None, False)

            gi_name = parameter.get_extension_attribute ('gi-extension', 'gi_name')

            parameter.extension_contents['type-link'] = self._format_linked_symbol (parameter)

        return HtmlFormatter._format_parameter_symbol (self, parameter)

    def _format_linked_symbol (self, symbol):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_linked_symbol (self, symbol)

        if not isinstance (symbol, QualifiedSymbol):
            return HtmlFormatter._format_linked_symbol (self, symbol)

        gi_name = symbol.get_extension_attribute ('gi-extension', 'gi_name')

        if gi_name is None:
            return HtmlFormatter._format_linked_symbol (self, symbol)

        if gi_name in self.fundamentals:
            return self._format_type_tokens ([self.fundamentals[gi_name]])

        return self._format_type_tokens (symbol.type_tokens)

    def _format_prototype (self, function, is_pointer, title):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_prototype (self, function,
                    is_pointer, title)

        params = function.get_extension_attribute ('gi-extension', 'parameters')

        if params is None:
            return HtmlFormatter._format_prototype (self, function,
                    is_pointer, title)

        for param in params:
            param.formatted_link = self._format_linked_symbol(param)

        c_name = function._make_name()

        if self.__gi_extension.language == 'python':
            template = self.engine.get_template('python_prototype.html')
        else:
            template = self.engine.get_template('javascript_prototype.html')

        if type (function) == SignalSymbol:
            comment = "%s callback for the '%s' signal" % (self.__gi_extension.language, c_name)
        elif type (function) == VFunctionSymbol:
            comment = "%s implementation of the '%s' virtual method" % \
                    (self.__gi_extension.language, c_name)
        else:
            comment = "%s wrapper for '%s'" % (self.__gi_extension.language,
                    c_name)

        res = template.render ({'return_value': function.return_value,
            'function_name': title, 'parameters':
            params, 'comment': comment, 'throws': function.throws,
            'out_params': [], 'is_method': function.is_method})

        return res

    def _format_property_summary (self, prop):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_property_summary (self, prop)

        template = self.engine.get_template('property_summary.html')
        property_type = None

        prop_link = self._format_linked_symbol (prop)

        return template.render({'property_type': property_type,
                                'property_link': prop_link,
                                'extra': prop.extension_contents,
                               })

    def _format_gi_vmethod_summary (self, vmethod):
        if self.__gi_extension.language == 'python':
            vmethod.link.title = 'do_%s' % vmethod._make_name()
        elif self.__gi_extension.language == 'javascript':
            vmethod.link.title = '%s::%s' % (vmethod.gi_parent_name, vmethod._make_name())
        return self._format_callable_summary (
                self._format_linked_symbol (vmethod.return_value),
                self._format_linked_symbol (vmethod),
                True,
                True,
                [])

    def _format_compound_summary (self, compound):
        template = self.engine.get_template('python_compound_summary.html')
        link = self._format_linked_symbol (compound)
        return template.render({'compound': link})

    def _format_struct_summary (self, struct):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_struct_summary (self, struct)
        return self._format_compound_summary (struct)

    def _format_enum_summary (self, enum):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_enum_summary (self, enum)
        return self._format_compound_summary (enum)

    def _format_alias_summary (self, alias):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_alias_summary (self, alias)
        return self._format_compound_summary (alias)

    def _format_constant_summary (self, constant):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_constant_summary (self, constant)
        return self._format_compound_summary (constant)

    def _format_gi_vmethod (self, vmethod):
        title = vmethod.link.title
        if self.__gi_extension.language == 'python':
            vmethod.link.title = 'do_%s' % vmethod._make_name()
            title = 'do_%s' % title
        elif self.__gi_extension.language == 'javascript':
            vmethod.link.title = '%s::%s' % (vmethod.gi_parent_name, vmethod._make_name())
            title = 'vfunc_%s' % title
        return self._format_callable (vmethod, "virtual method",
                title)

    def _format_struct (self, struct):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_struct (self, struct)
        members_list = self._format_members_list (struct.members, 'Attributes')

        template = self.engine.get_template ("python_compound.html")
        out = template.render ({"compound": struct,
                                "members_list": members_list})
        return (out, False)

    def _format_constant(self, constant):
        if self.__gi_extension.language == 'c':
            return HtmlFormatter._format_constant (self, constant)

        template = self.engine.get_template('constant.html')
        out = template.render ({'definition': None,
                                'constant': constant})
        return (out, False)

    def _get_style_sheet (self):
        if self.__gi_extension.language == 'python':
            return 'redstyle.css'
        elif self.__gi_extension.language == 'javascript':
            return 'greenstyle.css'
        return 'style.css'

    def _format_class (self, klass):
        new_names = None
        if self.__gi_extension.language == 'python':
            new_names = self.__gi_extension.gir_parser.python_names
        elif self.__gi_extension.language == 'javascript':
            new_names = self.__gi_extension.gir_parser.javascript_names

        if new_names is not None:
            self.doc_tool.page_parser.rename_headers (klass.parsed_page, new_names)
        return HtmlFormatter._format_class (self, klass)

    def format (self):
        for l in self.__gi_extension.languages:
            if l == 'python':
                self.fundamentals = self.python_fundamentals
            elif l == 'javascript':
                self.fundamentals = self.javascript_fundamentals
            else:
                self.fundamentals = {}

            for c_name, link in self.fundamentals.iteritems():
                prev_link = self.doc_tool.link_resolver.get_named_link(c_name)
                if prev_link:
                    prev_link.ref = link.ref
                    prev_link.title = link.title
                else:
                    link.id_ = c_name
                    self.doc_tool.link_resolver.add_link (link)

            self.__gi_extension.setup_language (l)
            self._output = os.path.join (self.doc_tool.output, l)
            if not os.path.exists (self._output):
                os.mkdir (self._output)
            HtmlFormatter.format (self)
