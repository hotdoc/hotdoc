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
import os
import shutil
import json
import io

from contextlib import redirect_stdout

from hotdoc.utils.utils import touch
from hotdoc.utils.loggable import Logger
from hotdoc.run_hotdoc import run


class TestHotdoc(unittest.TestCase):
    def setUp(self):
        self._test_dir = os.path.join(os.path.dirname(__file__), 'tmptestdir')
        try:
            shutil.rmtree(self._test_dir)
        except FileNotFoundError:
            pass
        os.mkdir(self._test_dir)
        os.chdir(self._test_dir)
        Logger.reset()
        self.__md_dir = os.path.abspath(os.path.join(
            self._test_dir, 'tmp-markdown-files'))
        self.__output_dir = os.path.abspath(os.path.join(
            self._test_dir, 'html'))
        self.__remove_tmp_dirs()
        os.mkdir(self.__md_dir)
        Logger.silent = True

    def tearDown(self):
        self.__remove_tmp_dirs()

    def __remove_tmp_dirs(self):
        shutil.rmtree(self.__md_dir, ignore_errors=True)
        shutil.rmtree(self.__output_dir, ignore_errors=True)
        for _ in os.listdir('.'):
            if _.startswith('hotdoc-private'):
                shutil.rmtree(_, ignore_errors=True)

    def __create_md_file(self, name, contents):
        path = os.path.join(self.__md_dir, name)
        with open(path, 'w') as _:
            _.write(contents)
        return path

    def __create_conf_file(self, name, conf):
        path = os.path.join(self._test_dir, name)
        with open(path, 'w') as _:
            _.write(json.dumps(conf))

        touch(path)
        return path

    def __create_sitemap(self, name, contents):
        path = os.path.join(self._test_dir, name)
        with open(path, 'w') as _:
            _.write(contents)

        touch(path)
        return path

    def assertOutput(self, n_html_files):
        actual = 0
        for f in os.listdir(os.path.join(self.__output_dir, 'html')):
            if f.endswith('.html'):
                actual += 1
        self.assertEqual(actual, n_html_files)

    def test_basic(self):
        self.__create_md_file('index.markdown',
                              "## A very simple index\n")

        with open(os.path.join(self.__md_dir, 'sitemap.txt'), 'w') as _:
            _.write('index.markdown')

        args = ['--index', os.path.join(self.__md_dir, 'index.markdown'),
                '--output', self.__output_dir,
                '--project-name', 'test-project',
                '--project-version', '0.1',
                '--sitemap', os.path.join(self.__md_dir, 'sitemap.txt'),
                'run']
        res = run(args)
        self.assertEqual(res, 0)

        self.assertOutput(1)

    def test_error(self):
        args = ['--index', os.path.join(self.__md_dir, 'index.markdown'),
                '--output', self.__output_dir,
                'run']
        res = run(args)
        self.assertEqual(res, 1)

    def test_explicit_conf_file(self):
        index_path = self.__create_md_file('index.markdown',
                                           "## A very simple index\n")
        sitemap_path = self.__create_sitemap('sitemap.txt', 'index.markdown')
        conf_path = self.__create_conf_file('explicit_hotdoc.json',
                                            {'index': index_path,
                                             'output': self.__output_dir,
                                             'project_name': 'test-project',
                                             'project_version': '0.1',
                                             'sitemap': sitemap_path})

        args = ['run', '--conf-file', conf_path]

        res = run(args)
        self.assertEqual(res, 0)
        self.assertOutput(1)

    def test_implicit_conf_file(self):
        index_path = self.__create_md_file('index.markdown',
                                           "## A very simple index\n")
        sitemap_path = self.__create_sitemap('sitemap.txt', 'index.markdown')
        self.__create_conf_file('hotdoc.json',
                                {'index': index_path,
                                 'output': self.__output_dir,
                                 'project_name': 'test-project',
                                 'project_version': '0.1',
                                 'sitemap': sitemap_path})

        args = ['run']

        res = run(args)
        self.assertEqual(res, 0)
        self.assertOutput(1)

    def test_conf(self):
        index_path = self.__create_md_file('index.markdown',
                                           "## A very simple index\n")
        sitemap_path = self.__create_sitemap('sitemap.txt', 'index.markdown')
        conf = {'index': index_path,
                'output': self.__output_dir,
                'project_name': 'test-project',
                'project_version': '0.1',
                'sitemap': sitemap_path}

        self.__create_conf_file('hotdoc.json', conf)
        args = ['conf']
        res = run(args)
        self.assertEqual(res, 0)
        with open(os.path.join(self._test_dir, 'hotdoc.json')) as _:
            updated_conf = json.loads(_.read())
        self.assertDictEqual(updated_conf, conf)

        args = ['conf', '--project-version', '0.2']
        res = run(args)
        self.assertEqual(res, 0)
        with open(os.path.join(self._test_dir, 'hotdoc.json')) as _:
            updated_conf = json.loads(_.read())
        self.assertEqual(updated_conf.get('project_version'), '0.2')

        conf = updated_conf
        args = ['conf', '--output-conf-file', 'new_hotdoc.json']
        res = run(args)
        self.assertEqual(res, 0)
        with open(os.path.join(self._test_dir, 'new_hotdoc.json')) as _:
            new_conf = json.loads(_.read())
        self.assertDictEqual(new_conf, conf)

        f = io.StringIO()
        args = ['--get-conf-key', 'project_version']
        with redirect_stdout(f):
            res = run(args)
        self.assertEqual(res, 0)
        self.assertEqual(f.getvalue().strip(), '0.2')

        f = io.StringIO()
        args = ['--get-conf-key', 'project_version',
                '--project-version', '0.3']
        with redirect_stdout(f):
            res = run(args)
        self.assertEqual(res, 0)
        self.assertEqual(f.getvalue().strip(), '0.3')

        f = io.StringIO()
        args = ['--get-conf-path', 'index']
        with redirect_stdout(f):
            res = run(args)
        self.assertEqual(res, 0)
        self.assertEqual(f.getvalue().strip(),
                         os.path.relpath(index_path, os.getcwd()))

    def test_version(self):
        from hotdoc.utils.setup_utils import VERSION
        args = ['--version']
        f = io.StringIO()
        with redirect_stdout(f):
            res = run(args)
        self.assertEqual(res, 0)
        self.assertEqual(f.getvalue().strip(), VERSION)

    def test_makefile_path(self):
        args = ['--makefile-path']
        f = io.StringIO()
        with redirect_stdout(f):
            res = run(args)
        self.assertEqual(res, 0)
        path = f.getvalue().strip()
        self.assertTrue(os.path.exists(path))

    def test_private_folder(self):
        self.__create_md_file('index.markdown',
                              "## A very simple index\n")

        with open(os.path.join(self.__md_dir, 'sitemap.txt'), 'w') as _:
            _.write('index.markdown')

        args = ['--index', os.path.join(self.__md_dir, 'index.markdown'),
                '--output', self.__output_dir,
                '--project-name', 'test-project',
                '--project-version', '0.1',
                '--sitemap', os.path.join(self.__md_dir, 'sitemap.txt'),
                '--get-private-folder']

        f = io.StringIO()
        with redirect_stdout(f):
            res = run(args)
        self.assertEqual(res, 0)
        path = f.getvalue().strip()
        self.assertTrue(os.path.basename(path).startswith('hotdoc-private'))
