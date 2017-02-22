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

from hotdoc.tests.fixtures import HotdocTest
from hotdoc.core.project import CoreExtension
from hotdoc.core.inclusions import find_file, resolve


class TestFileIncluder(HotdocTest):
    def setUp(self):
        super(TestFileIncluder, self).setUp()
        self._core_ext = CoreExtension(self, self)
        self._core_ext.setup()

    def test_missing_abspath(self):
        self.assertEqual(find_file('/nope.md', []), None)

    def test_abspath(self):
        path = self._create_md_file('yep.md', 'stuff')
        self.assertEqual(find_file(path, []), path)

    def test_relpath(self):
        path = self._create_md_file('yep.md', 'stuff')
        self.assertEqual(find_file('yep.md', [self._md_dir]), path)

    def test_missing_relpath(self):
        self.assertEqual(find_file('yep.md', [self._md_dir]), None)

    def test_resolve(self):
        _ = self._create_md_file('yep.md', 'stuff')
        self.assertEqual(resolve('yep.md', [self._md_dir]), 'stuff')

    def test_resolve_wrong_linenos(self):
        _ = self._create_md_file('yep.md', 'stuff')
        self.assertEqual(resolve('yep.md[4:7:9]', [self._md_dir]), None)
        self.assertEqual(resolve('yep.md[4:7]', [self._md_dir]), None)

    def test_resolve_linenos(self):
        _ = self._create_md_file('yep.md', 'foo\nbar\nbaz\nfoobar\n')
        self.assertEqual(resolve('yep.md[1:3]', [self._md_dir]), 'bar\nbaz\n')

    def test_resolve_different_lang(self):
        _ = self._create_src_file('yep.x', ['foo', 'bar', 'baz'])
        self.assertEqual(resolve('yep.x', [self._src_dir]),
                         '\n``` x\nfoo\nbar\nbaz\n\n```\n')

    def test_resolve_wrong_path(self):
        self.assertEqual(resolve('yep.x', []), None)
