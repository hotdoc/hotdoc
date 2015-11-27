import os

from ..core.base_extension import BaseExtension
from hotdoc.utils.loggable import Loggable, progress_bar
from dbusapi.interfaceparser import InterfaceParser
from hotdoc.core.symbols import *
from hotdoc.core.naive_index import NaiveIndexFormatter
from hotdoc.extensions.gi_raw_parser import GtkDocRawCommentParser


class DBusScanner(Loggable):
    def __init__(self, doc_tool, sources):
        Loggable.__init__(self)
        self.__current_filename = None
        self.symbols = {}
        self.doc_tool = doc_tool
        self.__raw_comment_parser = GtkDocRawCommentParser(self.doc_tool)
        for filename in sources:
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
            parameters.append (ParameterSymbol (argname=param.name,
                type_tokens=type_tokens,
                comment=param_comment))

        return parameters

    def __create_function_symbol (self, node):
        comment = '\n'.join([l.strip() for l in node.comment.split('\n')])
        comment = self.__raw_comment_parser.parse_comment (comment,
                self.__current_filename, 0, stripped=True)

        parameters = self.__create_parameters (node.arguments, comment)

        unique_name = '%s.%s' % (self.__current_class_name, node.name)
        self.doc_tool.get_or_create_symbol(FunctionSymbol,
                parameters=parameters,
                comment=comment,
                display_name=node.name,
                filename=self.__current_filename,
                unique_name=unique_name)

    def __create_class_symbol (self, node):
        self.__current_class_name = node.name
        comment = '\n'.join([l.strip() for l in node.comment.split('\n')])
        comment = self.__raw_comment_parser.parse_comment (comment,
                self.__current_filename, 0, stripped = True)
        self.doc_tool.get_or_create_symbol(ClassSymbol,
                comment=comment,
                display_name=node.name,
                filename=self.__current_filename)

    def __create_property_symbol (self, node):
        comment = '\n'.join([l.strip() for l in node.comment.split('\n')])
        comment = self.__raw_comment_parser.parse_comment (comment,
                self.__current_filename, 0, stripped = True)
        type_tokens = [node.type]
        type_ = QualifiedSymbol (type_tokens=type_tokens)

        flags = ''
        if node.access == node.ACCESS_READ:
            flags = 'Read'
        elif node.access == node.ACCESS_WRITE:
            flags = 'Write'
        elif node.access == node.ACCESS_READWRITE:
            flags = 'Read / Write'

        unique_name = '%s.%s' % (self.__current_class_name, node.name)
        sym = self.doc_tool.get_or_create_symbol(PropertySymbol,
                prop_type=type_, comment=comment,
                display_name=node.name,
                unique_name=unique_name,
                filename=self.__current_filename)

        if flags:
            sym.extension_contents['Flags'] = flags

    def __create_signal_symbol (self, node):
        comment = '\n'.join([l.strip() for l in node.comment.split('\n')])
        comment = self.__raw_comment_parser.parse_comment (comment,
                self.__current_filename, 0, stripped=True)

        parameters = self.__create_parameters (node.arguments, comment,
                omit_direction=True)

        unique_name = '%s.%s' % (self.__current_class_name, node.name)
        self.doc_tool.get_or_create_symbol(SignalSymbol,
                parameters=parameters, comment=comment,
                display_name=node.name, unique_name=unique_name,
                filename=self.__current_filename)

DESCRIPTION=\
"""
Parse DBus XML files and extract symbols and comments.
"""


class DBusExtension(BaseExtension):
    EXTENSION_NAME = 'dbus-extension'

    def __init__(self, doc_tool, config):
        BaseExtension.__init__(self, doc_tool, config)
        self.sources = config.get('dbus_sources')
        self.dbus_index = config.get('dbus_index')

        doc_tool.doc_tree.page_parser.register_well_known_name ('dbus-api',
                self.dbus_index_handler)

    def setup (self):
        if not self.sources:
            return

        self.scanner = DBusScanner (self.doc_tool, self.sources)

    @staticmethod
    def add_arguments (parser):
        group = parser.add_argument_group('DBus extension', DESCRIPTION)
        group.add_argument ("--dbus-sources", action="store", nargs="+",
                dest="dbus_sources", help="DBus interface files to parse")
        group.add_argument ("--dbus-index", action="store",
                dest="dbus_index",
                help="The dbus root markdown file")

    def dbus_index_handler(self, doc_tree):
        index_path = os.path.join(doc_tree.prefix, self.dbus_index)
        doc_tree.build_tree(index_path, self.EXTENSION_NAME)
        return index_path
