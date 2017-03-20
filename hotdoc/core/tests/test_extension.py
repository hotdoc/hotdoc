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
from hotdoc.tests.fixtures import HotdocTest
from hotdoc.core.extension import Extension
from hotdoc.core.symbols import FunctionSymbol
from hotdoc.utils.utils import OrderedSet


class HotdocTestExtension(Extension):
    extension_name = 'test-extension'
    argument_prefix = 'test'
    use_custom_key = False

    def __init__(self, app, project):
        self.smart_index = True
        self.name = 'test'
        super(HotdocTestExtension, self).__init__(app, project)

    def _get_smart_key(self, symbol):
        if not self.use_custom_key:
            return super(HotdocTestExtension, self)._get_smart_key(symbol)
        return symbol.extra['custom-key']

    def setup(self):
        stale, _ = self.get_stale_files(self.sources)
        for source in stale:
            with open(source, 'r') as _:
                lines = _.readlines()
                if self.use_custom_key:
                    custom_key = lines.pop(0).strip()
                else:
                    custom_key = None
                for l in lines:
                    l = l.strip()
                    self.get_or_create_symbol(
                        FunctionSymbol,
                        unique_name=l,
                        filename=source,
                        extra={'custom-key': custom_key})

    def get_created_symbols(self):
        return self._created_symbols


class TestExtension(HotdocTest):
    def setUp(self):
        self.project_name = 'test'
        super(TestExtension, self).setUp()
        self.test_ext = HotdocTestExtension(self, self)

    def tearDown(self):
        super(TestExtension, self).tearDown()
        del self.test_ext

    def test_smart_key_default(self):
        sources = []
        sources.append(self._create_src_file(
            'source_a.test',
            ['symbol_1']))
        self.test_ext.sources = sources
        self.test_ext.setup()
        self.assertDictEqual(self.test_ext.get_created_symbols(),
                             {sources[0]: OrderedSet(['symbol_1'])})

    def test_smart_key_custom(self):
        sources = []
        sources.append(self._create_src_file(
            'source_a.test',
            ['custom_key',
             'symbol_1']))
        self.test_ext.sources = sources
        self.test_ext.use_custom_key = True
        self.test_ext.setup()
        self.assertDictEqual(self.test_ext.get_created_symbols(),
                             {'custom_key': OrderedSet(['symbol_1'])})
