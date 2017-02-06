# -*- coding: utf-8 -*-
#
# Copyright © 2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2016 Collabora Ltd
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
# pylint: disable=invalid-name
# pylint: disable=no-self-use
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes
import unittest
import os
import shutil

from hotdoc.core.database import Database
from hotdoc.core.links import LinkResolver, Link
from hotdoc.core.symbols import (FunctionSymbol, ParameterSymbol, StructSymbol)


class TestLinkResolver(unittest.TestCase):
    def setUp(self):
        here = os.path.dirname(__file__)
        self.__priv_dir = os.path.abspath(os.path.join(
            here, 'tmp-private'))
        self.__remove_tmp_dirs()
        os.mkdir(self.__priv_dir)

        self.database = Database()
        self.database.setup(self.__priv_dir)
        self.link_resolver = LinkResolver(self.database)

    def __remove_tmp_dirs(self):
        shutil.rmtree(self.__priv_dir, ignore_errors=True)

    def test_incremental(self):
        param = ParameterSymbol(
            type_tokens=[Link(None, 'test-struct', 'test-struct')])
        func = self.database.get_or_create_symbol(
            FunctionSymbol, unique_name='test-symbol', filename='text_b.x',
            parameters=[param])

        func.resolve_links(self.link_resolver)

        self.assertEqual(param.get_type_link().get_link(self.link_resolver), None)

        struct = self.database.get_or_create_symbol(
            StructSymbol, unique_name='test-struct', filename='test_a.x')

        struct.resolve_links(self.link_resolver)
        func.resolve_links(self.link_resolver)

        # Not in a page but still
        self.assertEqual(param.get_type_link().get_link(self.link_resolver), 'test-struct')

        self.database.persist()
        self.database.close()

        self.database = Database()
        self.database.setup(self.__priv_dir)
        self.link_resolver = LinkResolver(self.database)

        param = ParameterSymbol(
            type_tokens=[Link(None, 'test-struct', 'test-struct')])
        func = self.database.get_or_create_symbol(
            FunctionSymbol, unique_name='test-symbol',
            filename='text_b.x', parameters=[param])

        func.resolve_links(self.link_resolver)
        self.assertEqual(param.get_type_link().get_link(self.link_resolver), 'test-struct')
