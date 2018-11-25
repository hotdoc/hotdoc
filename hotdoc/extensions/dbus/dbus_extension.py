# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import os, glob

from dbusapi.interfaceparser import InterfaceParser

from hotdoc.core.extension import Extension
from hotdoc.core.symbols import *
from hotdoc.parsers.gtk_doc import GtkDocParser
from hotdoc.utils.loggable import warn


class DBusScanner(object):
    def __init__(self, app, project, ext, sources):
        self.__current_filename = None
        self.symbols = {}
        self.project = project
        self.app = app
        self.__ext = ext
        self.__raw_comment_parser = GtkDocParser(self.project)
        for filename in sources:
            self.__current_filename = filename
            ip = InterfaceParser(filename)
            for name, interface in ip.parse().items():
                self.__create_class_symbol (interface)
                for mname, method in interface.methods.items():
                    self.__create_function_symbol (method)
                for pname, prop in interface.properties.items():
                    self.__create_property_symbol (prop)
                for sname, signal in interface.signals.items():
                    self.__create_signal_symbol (signal)

    def __create_parameters (self, nodes, omit_direction=False):
        parameters = []

        for param in nodes:
            type_tokens = []
            if not omit_direction:
                type_tokens.append (param.direction.upper() + ' ')

            type_tokens.append (str(param.type))
            parameters.append (ParameterSymbol (argname=param.name,
                type_tokens=type_tokens))

        return parameters

    def __comment_from_node(self, node, unique_name=None):
        if node.comment is None:
            return None

        lineno = -1

        lines = node.comment.split('\n')
        stripped_lines = []
        column_offset = 0
        line_offset = 0
        for l in lines:
            nl = l.strip()
            if not nl and not stripped_lines:
                line_offset += 1
                continue
            if not column_offset and nl:
                column_offset = len(l) - len(nl)
            stripped_lines.append(nl)

        if hasattr(node, 'comment_lineno'):
            lineno = node.comment_lineno + line_offset

        comment = u'\n'.join(stripped_lines)
        comment = self.__raw_comment_parser.parse_comment (comment,
                self.__current_filename, lineno,
                -1, stripped=True)

        if comment:
            comment.col_offset = column_offset + 1
            for param in list(comment.params.values()):
                param.col_offset = comment.col_offset

        if unique_name and comment:
            comment.name = unique_name

        return comment

    def __create_function_symbol (self, node):
        unique_name = '%s.%s' % (self.__current_class_name, node.name)
        comment = self.__comment_from_node(node, unique_name)
        self.__ext.add_comment(comment)
        parameters = self.__create_parameters (node.arguments)

        self.__ext.create_symbol(FunctionSymbol,
                parameters=parameters,
                display_name=node.name,
                filename=self.__current_filename,
                unique_name=unique_name)

    def __create_class_symbol (self, node):
        self.__current_class_name = node.name
        comment = self.__comment_from_node(node, node.name)
        self.__ext.add_comment(comment)
        self.__ext.create_symbol(ClassSymbol,
                display_name=node.name,
                filename=self.__current_filename)

    def __create_property_symbol (self, node):
        unique_name = '%s.%s' % (self.__current_class_name, node.name)
        comment = self.__comment_from_node(node, unique_name)
        self.__ext.add_comment(comment)

        type_tokens = [str(node.type)]
        type_ = QualifiedSymbol (type_tokens=type_tokens)

        flags = ''
        if node.access == node.ACCESS_READ:
            flags = 'Read'
        elif node.access == node.ACCESS_WRITE:
            flags = 'Write'
        elif node.access == node.ACCESS_READWRITE:
            flags = 'Read / Write'

        sym = self.__ext.create_symbol(PropertySymbol,
                prop_type=type_,
                display_name=node.name,
                unique_name=unique_name,
                filename=self.__current_filename)

        if sym and flags:
            sym.extension_contents['Flags'] = flags

    def __create_signal_symbol (self, node):
        unique_name = '%s.%s' % (self.__current_class_name, node.name)
        comment = self.__comment_from_node(node, unique_name)
        self.__ext.add_comment(comment)

        parameters = self.__create_parameters (node.arguments,
                omit_direction=True)

        self.__ext.create_symbol(SignalSymbol,
                parameters=parameters,
                display_name=node.name, unique_name=unique_name,
                filename=self.__current_filename)

DESCRIPTION=\
"""
Parse DBus XML files and extract symbols and comments.
"""


class DBusExtension(Extension):
    extension_name = 'dbus-extension'
    argument_prefix = 'dbus'

    def __init__(self, app, project):
        Extension.__init__(self, app, project)

    def setup (self):
        super(DBusExtension, self).setup()

        if not self.sources:
            return

        self.scanner = DBusScanner (self.app, self.project, self, self.sources)

    def create_symbol(self, *args, **kwargs):
        kwargs['language'] = 'dbus'
        return super(DBusExtension, self).create_symbol(*args,
            **kwargs)

    def _get_smart_index_title(self):
        return 'D-Bus API Reference'

    @staticmethod
    def add_arguments (parser):
        group = parser.add_argument_group('DBus extension',
                DESCRIPTION)
        DBusExtension.add_index_argument(group)
        DBusExtension.add_sources_argument(group)

def get_extension_classes():
    return [DBusExtension]
