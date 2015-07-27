# -*- coding: utf-8 -*-

from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.loader import FileLoader

from base_formatter import Formatter, LocalLink, ExternalLink, Link, QualifiedSymbol, ParameterSymbol
from base_formatter import FunctionSymbol, FunctionMacroSymbol, ClassSymbol, SectionSymbol
from yattag import Doc, indent

# We support that extension
from gi_extension.GIExtension import *

import uuid
import os

class Callable(object):
    def __init__(self, return_value, name, parameters):
        self.return_value = return_value
        self.name = name
        self.parameters = parameters

class TocSection (object):
    def __init__(self, summary, name):
        self.summary = summary
        self.name = name
        self.id_ = ''.join(name.split())

class SymbolDescriptions (object):
    def __init__(self, descriptions, name):
        self.descriptions = descriptions
        self.name = name

class HtmlFormatter (Formatter):
    def __init__(self, *args, **kwargs):
        Formatter.__init__(self, *args, **kwargs)
        self.__symbol_formatters = {
                FunctionSymbol: self._format_function,
                FunctionMacroSymbol: self._format_function_macro,
                GIClassSymbol: self._format_class,
                GIPropertySymbol: self._format_gi_property,
                GISignalSymbol: self._format_gi_signal,
                ClassSymbol: self._format_class,
                SectionSymbol: self._format_class,
                ParameterSymbol: self._format_parameter_symbol,
                }

        self.__summary_formatters = {
                FunctionSymbol: self._priv_format_function_summary,
                FunctionMacroSymbol: self._priv_format_function_macro_summary,
                GIPropertySymbol: self._format_gi_property_summary,
                GISignalSymbol: self._format_gi_signal_summary,
                }

        # Used to decide whether to render a separator
        module_path = os.path.dirname(__file__)
        searchpath = [os.path.join(module_path, "templates")]
        self.engine = Engine(
            loader=FileLoader(searchpath, encoding='UTF-8'),
            extensions=[CoreExtension()]
        )

    def _get_extension (self):
        return "html"

    def _priv_format_linked_symbol (self, symbol):
        template = self.engine.get_template('link.html')
        out = ""
        if isinstance (symbol, QualifiedSymbol):
            for tok in symbol.type_tokens:
                if isinstance (tok, Link):
                    out += '%s ' % template.render ({'link': tok.get_link(),
                                                     'link_title': tok.title,
                                            })
                else:
                    out += tok
        elif hasattr (symbol, "link"):
            out += template.render ({'link': symbol.link.get_link(),
                                     'link_title': symbol.link.title})

        if type (symbol) == ParameterSymbol:
            out += symbol.argname

        return out

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

    def _priv_format_parameter_detail (self, name, detail, annotations):
        template = self.engine.get_template('parameter_detail.html')
        return template.render ({'name': name,
                                 'detail': detail,
                                 'annotations': annotations,
                                })

    def _priv_format_symbol_detail (self, name, symbol_type, linkname,
            prototype, doc, retval, param_docs, flags=None):
        template = self.engine.get_template('symbol_detail.html')
        return template.render ({'name': name,
                                 'symbol_type': symbol_type,
                                 'linkname': linkname,
                                 'prototype': prototype,
                                 'doc': doc,
                                 'retval': retval,
                                 'param_docs': param_docs,
                                 'flags': flags,
                                })

    def _priv_format_enum_detail (self, enum):
        template = self.engine.get_template('enum_detail.html')
        return template.render ({'enum': enum})

    def _priv_format_callable_summary (self, return_value, function_name,
            is_callable, is_pointer, flags):
        template = self.engine.get_template('callable_summary.html')

        return template.render({'return_value': return_value,
                                'function_name': function_name,
                                'is_callable': is_callable,
                                'is_pointer': is_pointer,
                                'flags': flags
                               })

    def _priv_format_type_summary (self, type_type, type_name, flags=None): 
        template = self.engine.get_template('type_summary.html')

        return template.render({'type_type': type_type,
                                'type_name': type_name,
                                'flags': flags,
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
                param.formatted_doc, param.annotations))
        prototype = self._priv_format_callable_prototype (return_value,
                callable_.link.title, parameters, is_pointer)
        detail = self._priv_format_symbol_detail (callable_.link.title, symbol_type,
                callable_.link.get_link().split('#')[-1], prototype,
                callable_.formatted_doc, callable_.return_value, param_docs,
                callable_.flags)
        summary = self._priv_format_callable_summary (return_value, callable_link,
                is_callable, is_pointer, callable_.flags)

        return detail, summary

    def _priv_format_function (self, func):
        return self.__format_callable (func, func.type_name, "method")

    def _priv_format_function_summary (self, func):
        return self._priv_format_callable_summary (
                self._priv_format_linked_symbol (func.return_value),
                self._priv_format_linked_symbol (func),
                True,
                False,
                [])

    def _format_gi_signal_summary (self, signal):
        return self._priv_format_callable_summary (
                self._priv_format_linked_symbol (signal.return_value),
                self._priv_format_linked_symbol (signal),
                True,
                False,
                [])

    def _priv_format_function_macro_summary (self, func):
        return self._priv_format_callable_summary (
                "#define ",
                self._priv_format_linked_symbol (func),
                True,
                False,
                [])

    def _format_gi_property_summary (self, prop):
        template = self.engine.get_template('property_summary.html')
        property_type = self._priv_format_linked_symbol (prop.type_)
        prop_link = self._priv_format_linked_symbol (prop)

        return template.render({'property_type': property_type,
                                'property_link': prop_link,
                               })

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
            summary = self._priv_format_type_summary (directive, type_name,
                    type_.flags)
        else:
            summary = self._priv_format_type_summary (type_type, type_name,
                    type_.flags)

        prototype = self._priv_format_type_prototype (directive, type_type,
                type_.type_name)
        detail = self._priv_format_symbol_detail (name, member_type,
                type_.link.get_link().split('#')[-1], prototype,
                type_.formatted_doc, None, None, type_.flags)
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
                    param.formatted_doc, param.annotations))

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

    def _format_index (self, sections):
        template = self.engine.get_template('index_page.html')

        return template.render({'sections': sections})

    def _format_symbols_toc_section (self, symbols_type, symbols_list):
        summary_formatter = self.__summary_formatters.get(symbols_type)
        if not summary_formatter:
            return (None, None)

        toc_section_summaries = []
        detailed_descriptions = []
        
        for element in symbols_list.symbols:
            summary = summary_formatter(element)
            if summary:
                toc_section_summaries.append (summary)
            if element.detailed_description:
                detailed_descriptions.append (element.detailed_description)

        if not toc_section_summaries:
            return (None, None)

        summary = self._priv_format_summary (toc_section_summaries,
                symbols_list.name)
        toc_section = TocSection (summary, symbols_list.name)

        symbol_descriptions = None
        if detailed_descriptions:
            symbol_descriptions = SymbolDescriptions (detailed_descriptions,
                    symbols_list.name)

        return (toc_section, symbol_descriptions)

    def _format_class(self, klass):
        toc_sections = []
        symbols_details = []

        # Enforce our ordering
        for symbols_type in [FunctionSymbol, FunctionMacroSymbol,
                GIPropertySymbol, GISignalSymbol]:
            symbols_list = klass.typed_symbols.get(symbols_type)
            if not symbols_list:
                continue

            toc_section, symbols_descriptions = \
                    self._format_symbols_toc_section (symbols_type,
                            symbols_list)

            if toc_section:
                toc_sections.append(toc_section)
            if symbols_descriptions:
                symbols_details.append (symbols_descriptions) 

        template = self.engine.get_template('class2.html')
        out = template.render ({'klass': klass,
                                'toc_sections': toc_sections,
                                'symbols_details': symbols_details})

        return (out, True)

    def _format_gi_property(self, prop):
        type_link = self._priv_format_linked_symbol (prop.type_)
        template = self.engine.get_template('property_prototype.html')
        prototype = template.render ({'property_name': prop.link.title,
                                      'property_type': type_link})
        template = self.engine.get_template ('property.html')
        res = template.render ({'prototype': prototype,
                               'property': prop})
        return (res, False)

    def _format_prototype (self, function):
        return_value = self._priv_format_linked_symbol (function.return_value)
        parameters = []
        for param in function.parameters:
            parameters.append (self._priv_format_linked_symbol(param))

        return self._priv_format_callable_prototype (return_value,
                function.link.title, parameters, False)

    def _format_raw_code (self, code):
        template = self.engine.get_template('raw_code.html')
        return template.render ({'code': code})

    def _format_parameters (self, parameters):
        parameter_docs = []
        for param in parameters:
            parameter_docs.append (self._priv_format_parameter_detail
                    (param.argname, param.formatted_doc, []))
        return parameter_docs

    def _format_parameter_symbol (self, parameter):
        return (self._priv_format_parameter_detail (parameter.argname,
                parameter.formatted_doc, []), False)

    def _format_callable(self, callable_, callable_type):
        template = self.engine.get_template('callable.html')
        prototype = self._format_prototype (callable_)
        parameters = [p.detailed_description for p in callable_.parameters]

        out = template.render ({'prototype': prototype,
                                'callable': callable_,
                                'return_value': callable_.return_value,
                                'parameters': parameters,
                                'callable_type': callable_type})

        return (out, False)

    def _format_function(self, function):
        return self._format_callable (function, "method")

    def _format_gi_signal (self, signal):
        return self._format_callable (signal, "signal")

    def _format_function_macro(self, function_macro):
        template = self.engine.get_template('callable.html')
        prototype = self._format_raw_code (function_macro.original_text)
        parameters = [p.detailed_description for p in function_macro.parameters]

        out = template.render ({'prototype': prototype,
                                'callable': function_macro,
                                'return_value': None,
                                'parameters': parameters,
                                'callable_type': "function macro"})

        return (out, False)

    def _format_symbol (self, symbol):
        format_function = self.__symbol_formatters.get(type(symbol))
        if format_function:
            return format_function (symbol)
        return (None, False)
