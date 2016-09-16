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

import os
import shutil
import unittest

from hotdoc.core.comment_block import Comment
from hotdoc.core.doc_database import DocDatabase
from hotdoc.core.symbols import FunctionSymbol, ParameterSymbol, ReturnItemSymbol


class TestDocDatabase(unittest.TestCase):
    def setUp(self):
        self.__setup_tmp_dirs()
        self.doc_db = DocDatabase()
        self.doc_db.setup(self.__priv_dir)

    def tearDown(self):
        self.doc_db.close()
        self.__remove_tmp_dirs()

    def __reset_db(self):
        self.doc_db.flush()
        self.doc_db.persist()
        self.doc_db.close()
        self.doc_db = DocDatabase()
        self.doc_db.setup(self.__priv_dir)

    def __setup_tmp_dirs(self):
        here = os.path.dirname(__file__)
        self.__priv_dir = os.path.abspath(os.path.join(
            here, 'tmp-private'))
        self.__remove_tmp_dirs()
        os.mkdir(self.__priv_dir)

    def __remove_tmp_dirs(self):
        shutil.rmtree(self.__priv_dir, ignore_errors=True)

    def __create_test_function(self):
        params = []
        pcomment = Comment(name='bar', description='ze #bar')

        params.append(ParameterSymbol(argname='bar', type_tokens=['int'],
                                      comment=pcomment))

        retval = [ReturnItemSymbol(type_tokens=[], comment=None)]

        comment = Comment(name='foo', params={'bar': pcomment},
                          description='It does the foo')

        func = self.doc_db.get_or_create_symbol(
            FunctionSymbol, parameters=params, return_value=retval,
            comment=comment, display_name='foo')

        return func

    def test_basic(self):
        func = self.__create_test_function()
        self.assertEqual(func.unique_name, 'foo')
        same_func = self.doc_db.get_symbol('foo')
        self.assertEqual(func, same_func)

    def test_persist(self):
        func = self.__create_test_function()
        self.assertEqual(func.unique_name, 'foo')
        self.__reset_db()
        new_func = self.doc_db.get_symbol('foo')
        self.assertNotEqual(func, new_func)

    def test_update(self):
        func = self.__create_test_function()

        self.assertIsNone(func.filename)

        self.__reset_db()

        new_func = self.doc_db.get_or_create_symbol(
            FunctionSymbol, display_name='foo',
            filename='/plop.x')

        self.assertNotEqual(func, new_func)
        self.assertEqual(new_func.comment.description, 'It does the foo')
        self.assertEqual(new_func.filename, '/plop.x')

    def test_update_comment(self):
        self.__create_test_function()

        self.__reset_db()

        pcomment = Comment(name='bar', description='ze nicest #bar')

        comment = Comment(name='foo', params={'bar': pcomment},
                          description='It really does the foo')

        self.doc_db.add_comment(comment)

        new_func = self.doc_db.get_symbol('foo')
        self.assertEqual(new_func.comment.description, 'It really does the foo')

        pcomment = new_func.parameters[0].comment
        self.assertEqual(pcomment.description, 'ze nicest #bar')
