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
        ClassSymbol.__init__(self, **kwargs)

    def get_children_symbols(self):
        return [self.class_struct_symbol] + super().get_children_symbols()
