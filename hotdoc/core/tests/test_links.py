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
from hotdoc.core.links import LinkResolver, Link, dict_to_html_attrs
from hotdoc.core.symbols import (FunctionSymbol, ParameterSymbol, StructSymbol)
from hotdoc.utils.utils import OrderedDict


class TestLinkUtils(unittest.TestCase):
    def test_dict_to_html_attrs(self):
        self.assertEqual(dict_to_html_attrs({'foo': 'a.html#something'}),
                         'foo="a.html#something"')
        self.assertEqual(dict_to_html_attrs({'foo': None}),
                         'foo="None"')
        d = OrderedDict()
        d['foo'] = None
        d['bar'] = None
        self.assertEqual(dict_to_html_attrs(d), 'foo="None" bar="None"')
