# -*- coding: utf-8 -*-

import json
import os
import re
import tempfile

from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.loader import FileLoader

from ...core.symbols import *
from ...core.base_formatter import Formatter
from ...core.links import Link

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
    def __init__(self, searchpath, doc_tool):
        Formatter.__init__(self, doc_tool)

        self._symbol_formatters = {
                FunctionSymbol: self._format_function,
                FunctionMacroSymbol: self._format_function_macro,
                CallbackSymbol: self._format_callback,
                ConstantSymbol: self._format_constant,
                ExportedVariableSymbol: self._format_constant,
                AliasSymbol: self._format_alias,
                StructSymbol: self._format_struct,
                EnumSymbol: self._format_enum,
                ParameterSymbol: self._format_parameter_symbol,
                ReturnValueSymbol : self._format_return_value_symbol,
                FieldSymbol: self._format_field_symbol,
                SignalSymbol: self._format_signal_symbol,
                VFunctionSymbol: self._format_vfunction_symbol,
                PropertySymbol: self._format_property_symbol,
                ClassSymbol: self._format_class_symbol,
                }

        self._summary_formatters = {
                FunctionSymbol: self._format_function_summary,
                FunctionMacroSymbol: self._format_function_macro_summary,
                CallbackSymbol: self._format_callback_summary,
                ConstantSymbol: self._format_constant_summary,
                ExportedVariableSymbol: self._format_exported_variable_summary,
                AliasSymbol: self._format_alias_summary,
                StructSymbol: self._format_struct_summary,
                EnumSymbol: self._format_enum_summary,
                SignalSymbol: self._format_signal_summary,
                VFunctionSymbol: self._format_vfunction_summary,
                PropertySymbol: self._format_property_summary,
                ClassSymbol: self._format_class_summary,
                }

        self._ordering = [ClassSymbol, FunctionSymbol, FunctionMacroSymbol, SignalSymbol,
                PropertySymbol, StructSymbol, VFunctionSymbol, EnumSymbol, ConstantSymbol,
                ExportedVariableSymbol, AliasSymbol, CallbackSymbol]

        module_path = os.path.dirname(__file__)
        searchpath.append (os.path.join(module_path, "templates"))
        self.engine = Engine(
            loader=FileLoader(searchpath, encoding='UTF-8'),
            extensions=[CoreExtension()]
        )

    def _get_extension (self):
        return "html"

    def _format_link (self, link, title):
        out = ''
        if not link:
            print "Issue here plz check", title
            return title

        template = self.engine.get_template('link.html')
        out += '%s' % template.render ({'link': link,
                                         'link_title': title})
        return out

    def _format_type_tokens (self, type_tokens):
        out = ''
        link_before = False

        for tok in type_tokens:
            if isinstance (tok, Link):
                ref = tok.get_link()
                if ref:
                    out += self._format_link (ref, tok.title)
                    link_before = True
                else:
                    if link_before:
                        out += ' '
                    out += tok.title
                    link_before = False
            else:
                if link_before:
                    out += ' '
                out += tok
                link_before = False

        return out

    def _format_linked_symbol (self, symbol):
        out = ""

        if isinstance (symbol, QualifiedSymbol):
            out += self._format_type_tokens (symbol.type_tokens)

        elif hasattr (symbol, "link"):
            out += self._format_link (symbol.link.get_link(), symbol.link.title)

        if type (symbol) == ParameterSymbol:
            out += ' ' + symbol.argname

        if type (symbol) == FieldSymbol and symbol.member_name:
            template = self.engine.get_template('inline_code.html')
            member_name = template.render ({'code': symbol.member_name})
            if symbol.is_function_pointer:
                out = member_name
                out += "()"
            else:
                out += ' ' + member_name

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

    def __format_parameter_detail (self, name, detail, extra={}):
        template = self.engine.get_template('parameter_detail.html')
        return template.render ({'name': name,
                                 'detail': detail,
                                 'extra': extra
                                })

    def _format_callable_summary (self, return_value, function_name,
            is_callable, is_pointer):
        template = self.engine.get_template('callable_summary.html')

        return template.render({'return_value': return_value,
                                'function_name': function_name,
                                'is_callable': is_callable,
                                'is_pointer': is_pointer,
                               })

    def _format_function_summary (self, func):
        return self._format_callable_summary (
                self._format_linked_symbol (func.return_value),
                self._format_linked_symbol (func),
                True,
                False)

    def _format_callback_summary (self, callback):
        return self._format_callable_summary (
                self._format_linked_symbol (callback.return_value),
                self._format_linked_symbol (callback),
                True,
                True)

    def _format_function_macro_summary (self, func):
        return self._format_callable_summary (
                "#define ",
                self._format_linked_symbol (func),
                True,
                False)

    def _format_constant_summary (self, constant):
        template = self.engine.get_template('constant_summary.html')
        constant_link = self._format_linked_symbol (constant)
        return template.render({'constant': constant_link})

    def _format_exported_variable_summary (self, extern):
        template = self.engine.get_template('exported_variable_summary.html')
        extern_link = self._format_linked_symbol (extern)
        return template.render({'extern': extern_link})

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

    def _format_signal_summary (self, signal):
        return self._format_callable_summary (
                self._format_linked_symbol (signal.return_value),
                self._format_linked_symbol (signal),
                True,
                False)

    def _format_vfunction_summary (self, vmethod):
        return self._format_callable_summary (
                self._format_linked_symbol (vmethod.return_value),
                self._format_linked_symbol (vmethod),
                True,
                True)

    def _format_property_summary (self, prop):
        template = self.engine.get_template('property_summary.html')
        property_type = self._format_linked_symbol (prop.type_)

        prop_link = self._format_linked_symbol (prop)

        return template.render({'property_type': property_type,
                                'property_link': prop_link,
                                'extra': prop.extension_contents,
                               })

    def _format_class_summary (self, klass):
        if not klass.comment:
            return ''

        template = self.engine.get_template('class_summary.html')
        return template.render({'klass': klass})

    def _format_summary (self, summaries, summary_type):
        if not summaries:
            return None

        template = self.engine.get_template('summary.html')

        if summary_type == 'Classes':
            summary_type = ''

        return template.render({'summary_type': summary_type,
                                'summaries': summaries
                            })

    def _format_symbols_toc_section (self, symbols_type, symbols_list):
        summary_formatter = self._summary_formatters.get(symbols_type)
        if not summary_formatter:
            return (None, None)

        toc_section_summaries = []
        detailed_descriptions = []
        
        for element in symbols_list.symbols:
            if element.skip:
                continue
            summary = summary_formatter(element)
            if summary:
                toc_section_summaries.append (summary)
            if element.detailed_description:
                detailed_descriptions.append (element.detailed_description)

        if not toc_section_summaries:
            return (None, None)

        symbol_type = symbols_list.name

        summary = self._format_summary (toc_section_summaries,
                symbol_type)
        toc_section = TocSection (summary, symbol_type)

        symbol_descriptions = None
        if detailed_descriptions:
            if symbol_type == 'Classes':
                symbol_type = ''
            symbol_descriptions = SymbolDescriptions (detailed_descriptions,
                    symbol_type)

        return (toc_section, symbol_descriptions)

    def _format_struct (self, struct):
        raw_code = self._format_raw_code (struct.raw_text)
        members_list = self._format_members_list (struct.members, 'Fields')

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

        members_list = self._format_members_list (enum.members, 'Members')
        template = self.engine.get_template ("enum.html")
        out = template.render ({"enum": enum,
                                "members_list": members_list})
        return (out, False)

    def _format_page(self, page):
        if page.parsed_page and not page.symbols:
            page.formatted_contents = self.doc_tool.page_parser.render_parsed_page(page.parsed_page)

        toc_sections = []
        symbols_details = []

        for symbols_type in self._ordering:
            symbols_list = page.typed_symbols.get(symbols_type)
            if not symbols_list:
                continue

            toc_section, symbols_descriptions = \
                    self._format_symbols_toc_section (symbols_type,
                            symbols_list)

            if toc_section:
                toc_sections.append(toc_section)
            if symbols_descriptions:
                symbols_details.append (symbols_descriptions) 

        template = self.engine.get_template('page.html')

        out = template.render ({'page': page,
                                'toc_sections': toc_sections,
                                'stylesheet': self.__stylesheet,
                                'symbols_details': symbols_details})

        return (out, True)

    def _format_prototype (self, function, is_pointer, title):
        return_value = self._format_linked_symbol (function.return_value)
        parameters = []
        for param in function.parameters:
            parameters.append (self._format_linked_symbol(param))

        return self._format_callable_prototype (return_value,
                title, parameters, is_pointer)

    def _format_raw_code (self, code):
        template = self.engine.get_template('raw_code.html')
        return template.render ({'code': code})

    def _format_parameter_symbol (self, parameter):
        return (self.__format_parameter_detail (parameter.argname,
                parameter.formatted_doc, extra=parameter.extension_contents), False)

    def _format_field_symbol (self, field):
        field_id = self._format_linked_symbol (field) 
        return (self.__format_parameter_detail (field_id,
            field.formatted_doc), False)

    def _format_return_value_symbol(self, return_value):
        if not return_value or not return_value.formatted_doc:
            return ('', False)
        template = self.engine.get_template('return_value.html')
        return (template.render ({'return_value': return_value}), False)

    def _format_callable(self, callable_, callable_type, title,
            is_pointer=False):
        template = self.engine.get_template('callable.html')

        for p in callable_.parameters:
            p.do_format()

        parameters = [p.detailed_description for p in callable_.parameters if
                p.detailed_description is not None]

        prototype = self._format_prototype (callable_, is_pointer, title)

        return_value_detail = None
        if callable_.return_value:
            callable_.return_value.do_format()
            return_value_detail = callable_.return_value.detailed_description
        out = template.render ({'prototype': prototype,
                                'callable': callable_,
                                'return_value': return_value_detail,
                                'parameters': parameters,
                                'callable_type': callable_type,
                                'extra': callable_.extension_contents})

        return (out, False)

    def _format_signal_symbol (self, signal):
        title = "%s_callback" % re.sub ('-', '_', signal.link.title)
        return self._format_callable (signal, "signal", title)

    def _format_vfunction_symbol (self, vmethod):
        return self._format_callable (vmethod, "virtual method", vmethod.link.title)

    def _format_property_symbol (self, prop):
        type_link = self._format_linked_symbol (prop.type_)
        template = self.engine.get_template ('property_prototype.html')
        prototype = template.render ({'property_name': prop.link.title,
                                      'property_type': type_link})
        template = self.engine.get_template ('property.html')
        res = template.render ({'prototype': prototype,
                               'property': prop,
                               'extra': prop.extension_contents})
        return (res, False)

    def _format_class_symbol (self, klass):
        hierarchy = []
        children = []
        for p in klass.hierarchy:
            hierarchy.append(self._format_linked_symbol (p))
        for c in klass.children.itervalues():
            children.append(self._format_linked_symbol (c))

        if hierarchy or children:
            template = self.engine.get_template ("hierarchy.html")
            hierarchy = template.render ({'hierarchy': hierarchy,
                                        'children': children,
                                        'klass': klass})

        template = self.engine.get_template ('class.html')
        return (template.render ({'klass': klass,
                                  'hierarchy': hierarchy}),
                False)

    def _format_members_list(self, members, member_designation):
        template = self.engine.get_template('member_list.html')
        return template.render ({'members': members,
            'member_designation': member_designation})

    def _format_function(self, function):
        return self._format_callable (function, "method", function.link.title)

    def _format_callback (self, callback):
        return self._format_callable (callback, "callback",
                callback.link.title, is_pointer=True)

    def _format_function_macro(self, function_macro):
        template = self.engine.get_template('callable.html')
        prototype = self._format_raw_code (function_macro.original_text)

        for p in function_macro.parameters:
            p.do_format()

        parameters = [p.detailed_description for p in function_macro.parameters
                if p.detailed_description is not None]

        return_value_detail = None
        if function_macro.return_value:
            function_macro.return_value.do_format()
            return_value_detail = function_macro.return_value.detailed_description

        out = template.render ({'prototype': prototype,
                                'callable': function_macro,
                                'return_value': return_value_detail,
                                'parameters': parameters,
                                'callable_type': "function macro",
                                'flags': None,
                                'extra': function_macro.extension_contents})

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
        format_function = self._symbol_formatters.get(type(symbol))
        if format_function:
            return format_function (symbol)
        return (None, False)

    def _format_api_index (self, columns, rows):
        template = self.engine.get_template('API_index.html')
        rows.sort (key=lambda row: row[0].title)

        formatted_rows = []
        for row in rows:
            formatted_row = []
            for field in row:
                if isinstance(field, Link):
                    formatted_row.append (self._format_link(field.get_link(),
                        field.title))
                else:
                    formatted_row.append (field)
            formatted_rows.append (formatted_row)

        out = template.render ({'columns': columns,
                                'rows': formatted_rows,
                                'stylesheet': self.__stylesheet})

        return out

    def _format_class_hierarchy (self, dot_graph):
        f = tempfile.NamedTemporaryFile(suffix='.svg', delete=False)
        dot_graph.draw(f, prog='dot', format='svg', args="-Grankdir=LR")
        f.close()
        with open (f.name, 'r') as f:
            contents = f.read()
        os.unlink(f.name)

        template = self.engine.get_template('object_hierarchy.html')
        return template.render ({'graph': contents,
                                 'stylesheet': self.__stylesheet})

    def _get_style_sheet (self):
        return "style.css"

    def _get_extra_files (self):
        dir_ = os.path.dirname(__file__)
        return [os.path.join (dir_, self.__stylesheet),
                os.path.join (dir_, "API_index.js"),
                os.path.join (dir_, "home.png"),]

    def format (self):
        self.__stylesheet = self._get_style_sheet()
        Formatter.format(self)
