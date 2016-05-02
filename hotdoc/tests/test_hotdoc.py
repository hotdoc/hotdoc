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

from hotdoc.utils.loggable import Logger
from hotdoc.run_hotdoc import run


class TestHotdoc(unittest.TestCase):
    def setUp(self):
        here = os.path.dirname(__file__)
        Logger.reset()
        self.__md_dir = os.path.abspath(os.path.join(
            here, 'tmp-markdown-files'))
        self.__output_dir = os.path.abspath(os.path.join(
            here, 'html'))
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
        with open(os.path.join(self.__md_dir, name), 'w') as _:
            _.write(contents)

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
