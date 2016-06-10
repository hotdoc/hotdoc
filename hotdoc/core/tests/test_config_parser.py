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
                '"test_index": "/home/meh/test_index.markdown",\n'
                '"test_other_index": "other_index.markdown"\n'
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

        self.assertEqual(cp.get_index('test_other_'),
                         os.path.join(self.__priv_dir,
                                      'other_index.markdown'))

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

        deps = set([os.path.abspath(dep) for dep in cp.get_dependencies()])

        self.assertSetEqual(
            deps,
            set([os.path.join(self.__priv_dir, 'foo.x'),
                 os.path.join(self.__priv_dir, 'bar.x'),
                 os.path.join(self.__priv_dir, 'baz.x'),
                 conf_file]))

    def test_cli_overrides(self):
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
        touch(os.path.join(self.__priv_dir, 'foobar.x'))

        here = os.path.abspath(os.path.dirname(__file__))
        invoke_dir = os.getcwd()
        relpath = os.path.relpath(here, invoke_dir)
        overriden_src_dir = os.path.join(relpath, 'overridden_sources')

        shutil.rmtree(overriden_src_dir, ignore_errors=True)
        os.mkdir(overriden_src_dir)
        touch(os.path.join(overriden_src_dir, 'other.x'))
        touch(os.path.join(overriden_src_dir, 'foobar.x'))
        touch(os.path.join(overriden_src_dir, 'ignored.x'))

        cli = {'index': 'another_index.markdown',
               'test_sources': ['%s/*.x' % overriden_src_dir],
               'test_source_filters': ['%s/ignored.x' % overriden_src_dir]}

        cp = ConfigParser(command_line_args=cli, conf_file=conf_file)
        self.assertEqual(cp.get('index'), 'another_index.markdown')

        self.assertEqual(cp.get_index(),
                         os.path.join(invoke_dir, 'another_index.markdown'))

        overriden_abs_dir = os.path.join(invoke_dir, overriden_src_dir)

        self.assertSetEqual(
            set(cp.get_sources('test_')),
            set([os.path.join(overriden_abs_dir, 'other.x'),
                 os.path.join(overriden_abs_dir, 'foobar.x')]))

        shutil.rmtree(overriden_src_dir, ignore_errors=True)

    def test_dump(self):
        conf_file = os.path.join(self.__priv_dir, 'test.json')
        with open(conf_file, 'w') as _:
            _.write(
                '{\n'
                '"index": "my_index.markdown",\n'
                '"test_index": "/home/meh/test_index.markdown",\n'
                '"test_sources": ["*.x"],\n'
                '"test_source_filters": ["foobar.x"]\n'
                '}\n')

        here = os.path.abspath(os.path.dirname(__file__))
        invoke_dir = os.getcwd()
        relpath = os.path.relpath(here, invoke_dir)
        overriden_src_dir = os.path.join(relpath, 'overridden_sources')

        cli = {'index': 'another_index.markdown',
               'test_sources': ['%s/*.x' % overriden_src_dir],
               'test_source_filters': ['%s/ignored.x' % overriden_src_dir]}

        cp = ConfigParser(command_line_args=cli, conf_file=conf_file)
        cp.dump(conf_file=conf_file)
        ncp = ConfigParser(conf_file=conf_file)
        self.assertEqual(
            ncp.get_index(),
            os.path.join(invoke_dir, 'another_index.markdown'))
        self.assertListEqual(
            ncp.get('test_sources'),
            [u'../overridden_sources/*.x'])

    def test_path(self):
        conf_file = os.path.join(self.__priv_dir, 'test.json')
        with open(conf_file, 'w') as _:
            _.write(
                '{\n'
                '"my_path_argument": "somewhere/plop.x"\n'
                '}\n')

        cli = {'my_cli_path_argument': 'elsewhere/foo.x'}

        cp = ConfigParser(command_line_args=cli, conf_file=conf_file)
        self.assertEqual(
            cp.get_path('my_path_argument'),
            os.path.join(self.__priv_dir, 'somewhere', 'plop.x'))
        invoke_dir = os.getcwd()
        self.assertEqual(
            cp.get_path('my_cli_path_argument'),
            os.path.join(invoke_dir, 'elsewhere', 'foo.x'))
