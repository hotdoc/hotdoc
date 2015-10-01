import re, os
from hotdoc.core.doc_tool import doc_tool
from hotdoc.formatters.html.html_formatter import HtmlFormatter
from hotdoc.core.links import Link, ExternalLink
from hotdoc.core.symbols import *

class OverridenLink (Link):
    def __init__(self, link, title):
        Link.__init__(self)
        self.link = link
        self._title = title
        self.id_ = None

    def get_link(self):
        return self.link


class GIHtmlFormatter(HtmlFormatter):
    def __init__(self, gi_extension):
        module_path = os.path.dirname(__file__)
        searchpath = [os.path.join(module_path, "templates")]
        self.__gi_extension = gi_extension
        HtmlFormatter.__init__(self, searchpath)
        self.python_fundamentals = self.__create_python_fundamentals()
        self.javascript_fundamentals = self.__create_javascript_fundamentals()

    def __create_javascript_fundamentals(self):
        string_link = \
                OverridenLink('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/String',
                        'String')
        boolean_link = \
                OverridenLink('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Boolean',
                        'Boolean')
        pointer_link = \
                OverridenLink('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Object', 'Object')
        true_link = \
                OverridenLink('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Boolean',
                        'true')
        false_link = \
                OverridenLink('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/Boolean',
                        'false')
        number_link = \
                OverridenLink('https://developer.mozilla.org/en-US/docs/Glossary/Number',
                        'Number')
        null_link = \
                OverridenLink('https://developer.mozilla.org/en-US/docs/Web/'
                        'JavaScript/Reference/Global_Objects/null',
                        'null')

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
                OverridenLink('https://docs.python.org/2.7/library/functions.html#str',
                    'str')
        boolean_link = \
                OverridenLink('https://docs.python.org/2.7/library/functions.html#bool',
                        'bool')
        true_link = \
                OverridenLink('https://docs.python.org/2/library/constants.html#True',
                    'True')
        false_link = \
                OverridenLink('https://docs.python.org/2/library/constants.html#False',
                    'False')
        pointer_link = \
                OverridenLink('https://docs.python.org/2.7/library/functions.html#object',
                    'object')
        integer_link = \
                OverridenLink('https://docs.python.org/2/library/functions.html#int',
                        'int')
        float_link = \
                OverridenLink('https://docs.python.org/2/library/functions.html#float',
                        'float')
        none_link = \
                OverridenLink('https://docs.python.org/2/library/constants.html#None',
                        'None')
        unicode_link = \
                OverridenLink('https://docs.python.org/2/library/functions.html#unicode',
                        'unicode')

        gtype_link = \
                OverridenLink('https://developer.gnome.org/gobject/stable/'
                        'gobject-Type-Information.html#GType',
                        'GObject.Type')

        gvariant_link = \
                OverridenLink('https://developer.gnome.org/glib/stable/glib-GVariant.html',
                        'GLib.Variant')

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

    def _format_parameter_symbol_backup (self, parameter):
        template = self.engine.get_template('gi_parameter_detail.html')

        annotations = self.__gi_extension.get_annotations (parameter)
        if self.__gi_extension.language in ['python', 'javascript']:
            if hasattr(parameter, 'out') and parameter.out:
                return (None, False)
            annotations = []

        return (template.render ({'name': parameter.argname,
                                 'detail': parameter.formatted_doc,
                                 'annotations': annotations,
                                }), False)

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
        if self.__gi_extension.language in ["python", "javascript"]:
            params = []
            out_params = []
            retval = function.return_value
            for param in function.parameters:
                param.formatted_link = self._format_linked_symbol(param)
                if param.detailed_description is not None:
                    params.append (param)
                else:
                    out_params.append (param)

            if retval:
                gi_name = retval.get_extension_attribute ('gi-extension',
                        'gi_name')
                if gi_name == 'none':
                    retval = None
                else:
                    retval.formatted_link = self._format_linked_symbol(retval)

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

            res = template.render ({'return_value': retval,
                'function_name': title, 'parameters':
                params, 'comment': comment, 'throws': function.throws,
                'out_params': out_params, 'is_method': function.is_method})
            return res

        return HtmlFormatter._format_prototype (self, function,
            is_pointer, title)

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

    def _format_property_symbol(self, prop):
        type_link = self._format_linked_symbol (prop.type_)
        template = self.engine.get_template ('property_prototype.html')
        prototype = template.render ({'property_name': prop.link.title,
                                      'property_type': type_link})
        template = self.engine.get_template ('property.html')
        res = template.render ({'prototype': prototype,
                               'property': prop,
                               'extra': prop.extension_contents})
        return (res, False)

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
            doc_tool.page_parser.rename_headers (klass.parsed_page, new_names)
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
                link.id_ = c_name
                doc_tool.link_resolver.add_external_link (link)

            print "NOW DOING", l
            self.__gi_extension.setup_language (l)
            self._output = os.path.join (doc_tool.output, l)
            if not os.path.exists (self._output):
                os.mkdir (self._output)
            HtmlFormatter.format (self)
