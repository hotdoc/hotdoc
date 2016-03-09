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

import os
import unittest
import shutil

from hotdoc.core.doc_tree import DocTree
from hotdoc.core.symbols import FunctionSymbol
from hotdoc.core.doc_database import DocDatabase
from hotdoc.core.comment_block import Comment, Tag


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


class TestDocTree(unittest.TestCase):
    def setUp(self):
        here = os.path.dirname(__file__)
        self.__md_dir = os.path.join(here, 'tmp-markdown-files')
        self.__priv_dir = os.path.join(here, 'tmp-private')
        self.__remove_tmp_dirs()
        os.mkdir(self.__md_dir)
        os.mkdir(self.__priv_dir)
        self.doc_tree = DocTree([self.__md_dir],
                                os.path.join(here, 'tmp-private'))
        self.doc_db = DocDatabase()
        self.doc_db.setup(self.__priv_dir)

    def tearDown(self):
        self.__remove_tmp_dirs()
        self.doc_db.finalize()

    def __remove_tmp_dirs(self):
        shutil.rmtree(self.__md_dir, ignore_errors=True)
        shutil.rmtree(self.__priv_dir, ignore_errors=True)

    def __create_md_file(self, name, contents):
        with open(os.path.join(self.__md_dir, name), 'w') as _:
            _.write(contents)

    def __add_topic_symbol(self, topic, name):
        tags = {'topic': Tag('topic', description='', value=topic)}
        comment = Comment(name=name, tags=tags)
        # FIXME: make this unneeded
        self.doc_db.add_comment(comment)
        return self.doc_db.get_or_create_symbol(FunctionSymbol,
                                                display_name=name,
                                                comment=comment)

    def __persist(self):
        here = os.path.dirname(__file__)
        self.doc_tree.persist()
        self.doc_db.persist()
        self.doc_tree = DocTree([self.__md_dir],
                                os.path.join(here, 'tmp-private'))
        self.doc_db = DocDatabase()
        self.doc_db.setup(self.__priv_dir)

    def test_symbols_topics(self):
        self.__create_md_file('index.markdown',
                              "## Topic based documentation\n"
                              "\n"
                              "### [My topic]()\n")

        index_path = os.path.abspath(
            os.path.join(self.__md_dir, 'index.markdown'))

        root = self.doc_tree.build_tree(index_path)
        self.__add_topic_symbol('My topic', 'foo')
        self.assertSetEqual(set(root.symbol_names), {'foo'})

        # Now test incremental rebuild

        self.__persist()
        root = self.doc_tree.build_tree(index_path)
        self.assertFalse(root.is_stale)
        self.assertSetEqual(set(root.symbol_names), {'foo'})

        self.__persist()
        touch(index_path)
        root = self.doc_tree.build_tree(index_path)
        self.assertTrue(root.is_stale)
        self.assertSetEqual(set(root.symbol_names), {'foo'})

        self.__persist()
        root = self.doc_tree.build_tree(index_path)
        # We simulate staling of the "source file"
        self.__add_topic_symbol('My topic', 'foo')
        self.assertTrue(root.is_stale)
        self.assertSetEqual(set(root.symbol_names), {'foo'})
