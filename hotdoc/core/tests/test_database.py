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
    def test_redefined_symbol_same_run(self):
        self.database.get_or_create_symbol(
            FunctionSymbol,
            unique_name='foo')

        Logger.fatal_warnings = True
        Logger.silent = True
        with self.assertRaises(RedefinedSymbolException):
            self.database.get_or_create_symbol(
                FunctionSymbol,
                unique_name='foo')
        Logger.fatal_warnings = False
        Logger.silent = False

    # But when building incrementally, redefining a symbol should work
    # just fine
    def test_redefined_symbol_different_run(self):
        self.database.get_or_create_symbol(
            FunctionSymbol,
            unique_name='foo',
            display_name='bar')

        self.database.persist()
        self.database = Database(self.private_folder)

        # We get the symbol from the previous run
        sym = self.database.get_symbol('foo')
        self.assertIsNotNone(sym)
        self.assertEqual(sym.display_name, 'bar')

        # It is perfectly fine to update it in the new run
        Logger.fatal_warnings = True
        sym2 = self.database.get_or_create_symbol(
            FunctionSymbol,
            unique_name='foo',
            display_name='baz')
        Logger.fatal_warnings = False

        # The previous call will have updated and returned the symbol
        # we got initially
        self.assertEqual(sym, sym2)
        self.assertEqual(sym.display_name, 'baz')

        # It is invalid to update the symbol any further
        Logger.fatal_warnings = True
        Logger.silent = True
        with self.assertRaises(RedefinedSymbolException):
            sym2 = self.database.get_or_create_symbol(
                FunctionSymbol,
                unique_name='foo')
        Logger.fatal_warnings = False
        Logger.silent = False
