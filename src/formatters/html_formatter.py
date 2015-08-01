# -*- coding: utf-8 -*-

import json

from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.loader import FileLoader

from core.symbols import *
from core.base_formatter import Formatter
from core.links import Link
from pandoc_interface.pandoc_client import pandoc_converter

# We support the GNOME extension
from extensions.GIExtension import *

import os
import re

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
                CallbackSymbol: self._format_callback,
                ConstantSymbol: self._format_constant,
                AliasSymbol: self._format_alias,
                StructSymbol: self._format_struct,
                EnumSymbol: self._format_enum,
                GIClassSymbol: self._format_class,
                GIPropertySymbol: self._format_gi_property,
                GISignalSymbol: self._format_gi_signal,
                ClassSymbol: self._format_class,
                SectionSymbol: self._format_class,
                ParameterSymbol: self._format_parameter_symbol,
                FieldSymbol: self._format_field_symbol,
                }

        self.__summary_formatters = {
                FunctionSymbol: self._format_function_summary,
                FunctionMacroSymbol: self._format_function_macro_summary,
                CallbackSymbol: self._format_callback_summary,
                ConstantSymbol: self._format_constant_summary,
                AliasSymbol: self._format_alias_summary,
                StructSymbol: self._format_struct_summary,
                EnumSymbol: self._format_enum_summary,
                GIPropertySymbol: self._format_gi_property_summary,
                GISignalSymbol: self._format_gi_signal_summary,
                }

        module_path = os.path.dirname(__file__)
        searchpath = [os.path.join(module_path, "templates")]
        self.engine = Engine(
            loader=FileLoader(searchpath, encoding='UTF-8'),
            extensions=[CoreExtension()]
        )

    def _get_extension (self):
        return "html"

    def _get_pandoc_format (self):
        return "html"

    def _format_linked_symbol (self, symbol):
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

        if type (symbol) == FieldSymbol and symbol.member_name:
            template = self.engine.get_template('inline_code.html')
            member_name = template.render ({'code': symbol.member_name})
            if symbol.is_function_pointer:
                out = member_name
                out += "()"
            else:
                out += member_name

        return out

    def _format_callable_prototype (self, return_value, function_name,
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

    def _format_parameter_detail (self, name, detail, annotations):
        template = self.engine.get_template('parameter_detail.html')
        if not annotations:
            annotations = []
        return template.render ({'name': name,
                                 'detail': detail,
                                 'annotations': annotations,
                                })

    def _format_callable_summary (self, return_value, function_name,
            is_callable, is_pointer, flags):
        template = self.engine.get_template('callable_summary.html')

        return template.render({'return_value': return_value,
                                'function_name': function_name,
                                'is_callable': is_callable,
                                'is_pointer': is_pointer,
                                'flags': flags
                               })

    def _format_function_summary (self, func):
        return self._format_callable_summary (
                self._format_linked_symbol (func.return_value),
                self._format_linked_symbol (func),
                True,
                False,
                [])

    def _format_callback_summary (self, callback):
        return self._format_callable_summary (
                self._format_linked_symbol (callback.return_value),
                self._format_linked_symbol (callback),
                True,
                True,
                [])

    def _format_function_macro_summary (self, func):
        return self._format_callable_summary (
                "#define ",
                self._format_linked_symbol (func),
                True,
                False,
                [])

    def _format_constant_summary (self, constant):
        template = self.engine.get_template('constant_summary.html')
        constant_link = self._format_linked_symbol (constant)
        return template.render({'constant': constant_link})

    def _format_alias_summary (self, alias):
        template = self.engine.get_template('alias_summary.html')
        alias_link = self._format_linked_symbol (alias)
        return template.render({'alias': alias_link})

    def _format_struct_summary (self, struct):
        template = self.engine.get_template('struct_summary.html')
        struct_link = self._format_linked_symbol (struct)
        return template.render({'struct': struct_link})

    def _format_enum_summary (self, enum):
        template = self.engine.get_template('enum_summary.html')
        enum_link = self._format_linked_symbol (enum)
        return template.render({'enum': enum_link})

    def _format_summary (self, summaries, summary_type):
        if not summaries:
            return None
        template = self.engine.get_template('summary.html')
        return template.render({'summary_type': summary_type,
                                'summaries': summaries
                            })

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

        summary = self._format_summary (toc_section_summaries,
                symbols_list.name)
        toc_section = TocSection (summary, symbols_list.name)

        symbol_descriptions = None
        if detailed_descriptions:
            symbol_descriptions = SymbolDescriptions (detailed_descriptions,
                    symbols_list.name)

        return (toc_section, symbol_descriptions)

    def _format_struct (self, struct):
        raw_code = self._format_raw_code (struct.raw_text)
        members_list = self._format_members_list (struct.members)

        template = self.engine.get_template ("struct.html")
        out = template.render ({"struct": struct,
                          "raw_code": raw_code,
                          "members_list": members_list})
        return (out, False)

    def _format_enum (self, enum):
        for member in enum.members:
            template = self.engine.get_template ("enum_member.html")
            member.detailed_description = template.render ({
                                    'link': member.link,
                                    'detail': member.formatted_doc,
                                    'value': str (member.enum_value)})

        members_list = self._format_members_list (enum.members)
        template = self.engine.get_template ("enum.html")
        out = template.render ({"enum": enum,
                                "members_list": members_list})
        return (out, False)

    def _format_class(self, klass):
        toc_sections = []
        symbols_details = []

        # Enforce our ordering
        for symbols_type in [FunctionSymbol, FunctionMacroSymbol,
                GIPropertySymbol, GISignalSymbol, StructSymbol,
                EnumSymbol, ConstantSymbol, AliasSymbol, CallbackSymbol]:
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

        hierarchy = None
        if hasattr (klass, 'hierarchy') and klass.hierarchy:
            hierarchy = []
            children = []
            for p in klass.hierarchy:
                hierarchy.append(self._format_linked_symbol (p))
            for c in klass.children:
                children.append(self._format_linked_symbol (c))

            template = self.engine.get_template ("hierarchy.html")
            hierarchy = template.render ({'hierarchy': hierarchy,
                                          'children': children,
                                          'klass': klass})

        template = self.engine.get_template('class.html')
        if klass.parsed_contents:
            klass.formatted_contents = pandoc_converter.convert("json", "html",
                    json.dumps(klass.parsed_contents))

        out = template.render ({'klass': klass,
                                'hierarchy': hierarchy,
                                'toc_sections': toc_sections,
                                'symbols_details': symbols_details})

        return (out, True)

    def _format_prototype (self, function, is_pointer):
        return_value = self._format_linked_symbol (function.return_value)
        parameters = []
        for param in function.parameters:
            parameters.append (self._format_linked_symbol(param))

        title = function.link.title
        if type (function) == GISignalSymbol:
            title = "%s_callback" % re.sub ('-', '_', title)
        return self._format_callable_prototype (return_value,
                title, parameters, is_pointer)

    def _format_raw_code (self, code):
        template = self.engine.get_template('raw_code.html')
        return template.render ({'code': code})

    def _format_parameter_symbol (self, parameter):
        annotations = parameter.get_extension_attribute (GIExtension, "annotations")
        return (self._format_parameter_detail (parameter.argname,
                parameter.formatted_doc, annotations), False)

    def _format_field_symbol (self, field):
        field_id = self._format_linked_symbol (field) 
        return (self._format_parameter_detail (field_id,
            field.formatted_doc, []), False)

    def _format_callable(self, callable_, callable_type, is_pointer=False, flags=None):
        template = self.engine.get_template('callable.html')
        prototype = self._format_prototype (callable_, is_pointer)
        parameters = [p.detailed_description for p in callable_.parameters]

        return_annotations = []
        if callable_.return_value:
            annotations = callable_.return_value.get_extension_attribute (GIExtension, "annotations")
            if annotations:
                return_annotations = annotations

        out = template.render ({'prototype': prototype,
                                'callable': callable_,
                                'return_value': callable_.return_value,
                                'return_annotations': return_annotations,
                                'parameters': parameters,
                                'callable_type': callable_type,
                                'flags': flags})

        return (out, False)

    def _format_members_list(self, members):
        template = self.engine.get_template('member_list.html')
        return template.render ({'members': members})

    def _format_function(self, function):
        return self._format_callable (function, "method")

    def _format_callback (self, callback):
        return self._format_callable (callback, "callback", is_pointer=True)

    def _format_function_macro(self, function_macro):
        template = self.engine.get_template('callable.html')
        prototype = self._format_raw_code (function_macro.original_text)
        parameters = [p.detailed_description for p in function_macro.parameters]

        out = template.render ({'prototype': prototype,
                                'callable': function_macro,
                                'return_value': function_macro.return_value,
                                'return_annotations': None,
                                'parameters': parameters,
                                'callable_type': "function macro",
                                'flags': None})

        return (out, False)

    def _format_alias (self, alias):
        template = self.engine.get_template('alias.html')
        aliased_type = self._format_linked_symbol (alias.aliased_type)
        return (template.render ({'alias': alias, 'aliased_type':
                aliased_type}), False)

    def _format_constant(self, constant):
        template = self.engine.get_template('constant.html')
        definition = self._format_raw_code (constant.original_text)
        out = template.render ({'definition': definition,
                                'constant': constant})
        return (out, False)

    def _format_symbol (self, symbol):
        format_function = self.__symbol_formatters.get(type(symbol))
        if format_function:
            return format_function (symbol)
        return (None, False)

    # GNOME extension

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
        return self._format_callable (signal, "signal", flags=signal.flags)

    def _format_gi_property(self, prop):
        type_link = self._format_linked_symbol (prop.type_)
        template = self.engine.get_template('property_prototype.html')
        prototype = template.render ({'property_name': prop.link.title,
                                      'property_type': type_link})
        template = self.engine.get_template ('property.html')
        res = template.render ({'prototype': prototype,
                               'property': prop})
        return (res, False)
