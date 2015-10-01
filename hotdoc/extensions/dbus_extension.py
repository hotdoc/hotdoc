import os

from ..core.base_extension import BaseExtension
from ..core.dependencies import DependencyTree
from hotdoc.utils.loggable import Loggable, progress_bar
from hotdoc.extensions.common_mark_parser import CommonMarkParser
from dbusapi.interfaceparser import InterfaceParser
from hotdoc.core.doc_tool import doc_tool
from hotdoc.formatters.html.html_formatter import HtmlFormatter
from hotdoc.core.symbols import *
from hotdoc.core.naive_index import NaiveIndexFormatter

class Location:
    def __init__(self, filename, lineno):
        self.file = filename
        self.lineno = lineno

class DBusScanner(Loggable):
    def __init__(self, sources):
        Loggable.__init__(self)
        self.__current_filename = None
        self.symbols = {}
        for filename in sources:
            self.__current_filename = filename
            print "parsing", filename
            ip = InterfaceParser(filename)
            for name, interface in ip.parse().iteritems():
                self.__create_class_symbol (interface)
                for mname, method in interface.methods.iteritems():
                    self.__create_function_symbol (method)
                for pname, prop in interface.properties.iteritems():
                    self.__create_property_symbol (prop)
                for sname, signal in interface.signals.iteritems():
                    self.__create_signal_symbol (signal)
        #nif = NaiveIndexFormatter(self.symbols)

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

        loc = Location (self.__current_filename, 0)
        sym = PropertySymbol (type_, self.__current_class_name, comment,
                node.name, location=loc)

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


class DBusExtension(BaseExtension):
    EXTENSION_NAME = 'dbus-extension'

    def __init__(self, args):
        self.sources = args.dbus_sources
        self.index_file = args.dbus_index
        self.scanner = DBusScanner (self.sources)
        self.page_parser = CommonMarkParser ()

    def setup (self):
        deps_file = 'dbus_dependencies.p'
        self.output = os.path.join(doc_tool.output, 'dbus')
        if not os.path.exists (self.output):
            os.mkdir (self.output)
        self.dependency_tree = DependencyTree (os.path.join(doc_tool.output, deps_file),
                [os.path.abspath (f) for f in self.sources])
        self.page_parser.create_symbols(self)
        self.pages = self.page_parser.pages
        self.formatter = HtmlFormatter([], self)

    def build_extra_symbols (self):
        self.formatter.format()

    def get_symbol (self, symbol_name):
        return self.scanner.symbols.get (symbol_name)

    @staticmethod
    def add_arguments (parser):
        parser.add_argument ("--dbus-sources", action="store", nargs="+",
                dest="dbus_sources", help="DBus interface files to parse",
                default=[], required = True)
        parser.add_argument ("--dbus-index", action="store",
                dest="dbus_index", help="location of the dbus index file",
                required = True)
