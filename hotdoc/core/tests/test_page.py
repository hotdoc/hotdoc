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
# pylint: disable=import-error
# pylint: disable=no-self-use
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes
import unittest

from schema import Optional, And

from hotdoc.core.tree import Page, InvalidPageMetadata
from hotdoc.utils.loggable import Logger


class TestPage(unittest.TestCase):
    def setUp(self):
        Logger.silent = True
        Logger.fatal_warnings = True
        Logger.raise_on_fatal_warnings = True

    def tearDown(self):
        Logger.silent = False
        Logger.fatal_warnings = False
        Logger.reset()

    def test_meta_schema(self):
        meta = {'foo': u'bar'}
        with self.assertRaises(InvalidPageMetadata):
            page = Page('some-page', True, 'test-project-0.1', 'core', meta=meta)
        Page.meta_schema[Optional('foo')] = And(str, len)
        page = Page('some-page', True, 'test-project-0.1', 'core', meta=meta)
        self.assertEqual(page.meta.get('foo'), u'bar')
