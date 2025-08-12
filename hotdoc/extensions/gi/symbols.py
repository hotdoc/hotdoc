# -*- coding: utf-8 -*-
#
# Copyright © 2017 Thibault Saunier <tsaunier@gnome.org>
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

from hotdoc.core.symbols import *


class GIClassSymbol(ClassSymbol):
    def __init__(self, **kwargs):
        self.class_struct_symbol = None
        self.interfaces = []
        self.properties = []
        self.methods = []
        self.signals = []
        self.vfuncs = []
        ClassSymbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        res = self.interfaces + self.properties + self.methods + \
            self.signals + self.vfuncs + super().get_children_symbols()

        if self.class_struct_symbol:
            res += [self.class_struct_symbol] + \
                self.class_struct_symbol.get_children_symbols()

        return res


class GIInterfaceSymbol(InterfaceSymbol):
    def __init__(self, **kwargs):
        self.class_struct_symbol = None
        self.properties = []
        self.methods = []
        self.signals = []
        self.vfuncs = []
        InterfaceSymbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        res = self.properties + self.methods + self.signals + \
            self.vfuncs + super().get_children_symbols()
        if self.class_struct_symbol:
            res += [self.class_struct_symbol] + \
                self.class_struct_symbol.get_children_symbols()

        return res


class GIStructSymbol(ClassSymbol):
    """Boxed types are pretty much handled like classes with a possible
       constructors, methods, etc... we render them as such.
    """

    def __init__(self, **kwargs):
        self.class_struct_symbol = None
        self.methods = []
        ClassSymbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return [self.class_struct_symbol] + self.methods + super().get_children_symbols()
