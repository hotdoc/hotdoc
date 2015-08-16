import re, os
from better_doc_tool.formatters.html.html_formatter import HtmlFormatter

class GIHtmlFormatter(HtmlFormatter):
    def __init__(self, gi_extension):
        from better_doc_tool.extensions.gi_extension import (GIClassSymbol,
                GIPropertySymbol, GISignalSymbol)

        module_path = os.path.dirname(__file__)
        searchpath = [os.path.join(module_path, "templates")]
        HtmlFormatter.__init__(self, searchpath)
        self.__gi_extension = gi_extension
        self._symbol_formatters[GIClassSymbol] = self._format_class
        self._symbol_formatters[GIPropertySymbol] = self._format_gi_property
        self._summary_formatters[GIPropertySymbol] = self._format_gi_property_summary
        self._symbol_formatters[GISignalSymbol] = self._format_gi_signal
        self._summary_formatters[GISignalSymbol] = self._format_gi_signal_summary
        self._ordering.insert (2, GIPropertySymbol)
        self._ordering.insert (3, GISignalSymbol)

    def _format_parameter_symbol (self, parameter):
        annotations = self.__gi_extension.get_annotations (parameter)
        template = self.engine.get_template('gi_parameter_detail.html')
        return (template.render ({'name': parameter.argname,
                                 'detail': parameter.formatted_doc,
                                 'annotations': annotations,
                                }), False)

    def _format_return_value_symbol (self, return_value):
        if not return_value or not return_value.formatted_doc:
            return ('', False)
        template = self.engine.get_template('gi_return_value.html')
        annotations = self.__gi_extension.get_annotations (return_value)
        return (template.render ({'return_value': return_value,
                                  'annotations': annotations}), False)

    def _format_gi_property_summary (self, prop):
        template = self.engine.get_template('property_summary.html')
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

    def _format_gi_signal (self, signal):
        title = "%s_callback" % re.sub ('-', '_', signal.link.title)
        return self._format_callable (signal, "signal", title, flags=signal.flags)

    def _format_gi_property(self, prop):
        type_link = self._format_linked_symbol (prop.type_)
        template = self.engine.get_template('property_prototype.html')
        prototype = template.render ({'property_name': prop.link.title,
                                      'property_type': type_link})
        template = self.engine.get_template ('property.html')
        res = template.render ({'prototype': prototype,
                               'property': prop})
        return (res, False)
