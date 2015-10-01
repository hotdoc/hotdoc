from hotdoc.utils.loggable import Loggable, progress_bar
from dbusapi.interfaceparser import InterfaceParser
from hotdoc.core.doc_tool import doc_tool
from hotdoc.core.symbols import *

class Location:
    def __init__(self, filename, lineno):
        self.file = filename
        self.lineno = lineno

class DBusScanner(Loggable):
    def __init__(self):
        Loggable.__init__(self)
        self.__current_filename = None
        self.symbols = {}
        for filename in doc_tool.dbus_sources:
            self.__current_filename = filename
            ip = InterfaceParser(filename)
            for name, interface in ip.parse().iteritems():
                self.__create_class_symbol (interface)
                for mname, method in interface.methods.iteritems():
                    self.__create_function_symbol (method)
                for pname, prop in interface.properties.iteritems():
                    self.__create_property_symbol (prop)
                for sname, signal in interface.signals.iteritems():
                    self.__create_signal_symbol (signal)

    def __create_parameters (self, nodes, comment, omit_direction=False):
        parameters = []

        for param in nodes:
            if comment:
                param_comment = comment.params.get (param.name)
            else:
                param_comment = None

            type_tokens = []
            if not omit_direction:
                type_tokens.append (param.direction.upper() + ' ')
            type_tokens.append (param.type)
            parameters.append (ParameterSymbol (param.name, type_tokens,
                param_comment))

        return parameters

    def __create_function_symbol (self, node):
        comment = '\n'.join([l.strip() for l in node.comment.split('\n')])
        comment = doc_tool.raw_comment_parser.parse_comment (comment,
                self.__current_filename, 0, stripped=True)

        parameters = self.__create_parameters (node.arguments, comment)

        loc = Location (self.__current_filename, 0)
        sym = FunctionSymbol (parameters, None, comment, node.name,
                loc)

        self.symbols['%s.%s' % (self.__current_class_name, node.name)] = sym

    def __create_class_symbol (self, node):
        self.__current_class_name = node.name
        comment = '\n'.join([l.strip() for l in node.comment.split('\n')])
        comment = doc_tool.raw_comment_parser.parse_comment (comment,
                self.__current_filename, 0, stripped = True)
        loc = Location (self.__current_filename, 0)
        sym = ClassSymbol ([], {}, comment, node.name, loc)
        self.symbols[node.name] = sym

    def __create_property_symbol (self, node):
        comment = '\n'.join([l.strip() for l in node.comment.split('\n')])
        comment = doc_tool.raw_comment_parser.parse_comment (comment,
                self.__current_filename, 0, stripped = True)
        type_tokens = [node.type]
        type_ = QualifiedSymbol (type_tokens, None)

        flags = ''
        if node.access == node.ACCESS_READ:
            flags = 'Read'
        elif node.access == node.ACCESS_WRITE:
            flags = 'Write'
        elif node.access == node.ACCESS_READWRITE:
            flags = 'Read / Write'

        sym = PropertySymbol (type_, self.__current_class_name, comment,
                node.name)

        if flags:
            sym.extension_contents['Flags'] = flags

        self.symbols['%s.%s' % (self.__current_class_name, node.name)] = sym

    def __create_signal_symbol (self, node):
        comment = '\n'.join([l.strip() for l in node.comment.split('\n')])
        comment = doc_tool.raw_comment_parser.parse_comment (comment,
                self.__current_filename, 0, stripped=True)

        parameters = self.__create_parameters (node.arguments, comment,
                omit_direction=True)

        loc = Location (self.__current_filename, 0)
        sym = SignalSymbol (self.__current_class_name, parameters, None, comment, node.name,
                loc)

        self.symbols['%s.%s' % (self.__current_class_name, node.name)] = sym
