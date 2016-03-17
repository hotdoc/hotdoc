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

import unittest
import shutil
import os

from hotdoc.core.config import ConfigParser
from hotdoc.utils.utils import touch


class TestConfigParser(unittest.TestCase):
    def setUp(self):
        here = os.path.dirname(__file__)
        priv_dir = os.path.join(here, 'test-private')
        self.__priv_dir = os.path.abspath(priv_dir)
        shutil.rmtree(self.__priv_dir, ignore_errors=True)
        os.mkdir(self.__priv_dir)

    def tearDown(self):
        shutil.rmtree(self.__priv_dir, ignore_errors=True)

    def test_index(self):
        conf_file = os.path.join(self.__priv_dir, 'test.json')
        with open(conf_file, 'w') as _:
            _.write(
                '{\n'
                '"index": "my_index.markdown",\n'
                '"test_index": "/home/meh/test_index.markdown"\n'
                '}\n')

        cp = ConfigParser(conf_file=conf_file)

        # A relative path was passed, the parser should return an
        # absolute path with the path to the conf file as root.
        self.assertEqual(cp.get_index(),
                         os.path.join(self.__priv_dir, 'my_index.markdown'))

        # An absolute path was passed, and must thus be retrieved
        self.assertEqual(cp.get_index('test_'),
                         '/home/meh/test_index.markdown')

        self.assertIsNone(cp.get_index('invalid_prefix'))

    def test_sources(self):
        conf_file = os.path.join(self.__priv_dir, 'test.json')
        with open(conf_file, 'w') as _:
            _.write(
                '{\n'
                '"test_sources": ["*.x"],\n'
                '"test_source_filters": ["foobar.x"]\n'
                '}\n')

        touch(os.path.join(self.__priv_dir, 'foo.x'))
        touch(os.path.join(self.__priv_dir, 'bar.x'))
        touch(os.path.join(self.__priv_dir, 'baz.x'))
        touch(os.path.join(self.__priv_dir, 'foobar.x'))

        cp = ConfigParser(conf_file=conf_file)
        self.assertSetEqual(
            set(cp.get_sources('test_')),
            set([os.path.join(self.__priv_dir, 'foo.x'),
                 os.path.join(self.__priv_dir, 'bar.x'),
                 os.path.join(self.__priv_dir, 'baz.x')]))

    def test_dependencies(self):
        conf_file = os.path.join(self.__priv_dir, 'test.json')
        with open(conf_file, 'w') as _:
            _.write(
                '{\n'
                '"index": "my_index.markdown",\n'
                '"test_index": "/home/meh/test_index.markdown",\n'
                '"test_sources": ["*.x"],\n'
                '"test_source_filters": ["foobar.x"]\n'
                '}\n')

        touch(os.path.join(self.__priv_dir, 'foo.x'))
        touch(os.path.join(self.__priv_dir, 'bar.x'))
        touch(os.path.join(self.__priv_dir, 'baz.x'))
        touch(os.path.join(self.__priv_dir, 'foobar.x'))

        cp = ConfigParser(conf_file=conf_file)

        self.assertSetEqual(
            set(cp.get_dependencies()),
            set([os.path.join(self.__priv_dir, 'foo.x'),
                 os.path.join(self.__priv_dir, 'bar.x'),
                 os.path.join(self.__priv_dir, 'baz.x'),
                 os.path.join(self.__priv_dir, 'my_index.markdown'),
                 '/home/meh/test_index.markdown']))
