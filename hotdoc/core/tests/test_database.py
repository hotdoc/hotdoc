# -*- coding: utf-8 -*-
#
# Copyright © 2018 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
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

# pylint: disable=missing-docstring
from hotdoc.tests.fixtures import HotdocTest
from hotdoc.core.database import Database, RedefinedSymbolException
from hotdoc.core.symbols import FunctionSymbol
from hotdoc.utils.loggable import Logger


class TestDatabase(HotdocTest):
    # Defining the same symbol twice in the same run is not allowed
    def test_redefined_symbol(self):
        self.database.create_symbol(
            FunctionSymbol,
            unique_name='foo')

        Logger.fatal_warnings = True
        Logger.silent = True
        with self.assertRaises(RedefinedSymbolException):
            self.database.create_symbol(
                FunctionSymbol,
                unique_name='foo')
        Logger.fatal_warnings = False
        Logger.silent = False
