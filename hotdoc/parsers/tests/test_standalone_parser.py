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
import shutil
import io
import os

from hotdoc.core.change_tracker import ChangeTracker
from hotdoc.core.doc_database import DocDatabase
from hotdoc.core.links import LinkResolver
from hotdoc.core.symbols import FunctionSymbol
from hotdoc.parsers import cmark
from hotdoc.parsers.standalone_parser import (
    SitemapParser, SitemapDuplicateError,
    SitemapError, Extension, DocTree)
from hotdoc.utils.utils import IndentError, OrderedSet, touch
from hotdoc.utils.loggable import Logger


class TestSitemapParser(unittest.TestCase):

    def setUp(self):
        here = os.path.dirname(__file__)
        self.__tmp_dir = os.path.abspath(os.path.join(
            here, 'sitemap-test'))
        shutil.rmtree(self.__tmp_dir, ignore_errors=True)
        os.mkdir(self.__tmp_dir)
        self.parser = SitemapParser()
        Logger.silent = True

    def tearDown(self):
        shutil.rmtree(self.__tmp_dir, ignore_errors=True)

    def parse(self, text):
        path = os.path.join(self.__tmp_dir, 'sitemap.txt')
        with io.open(path, 'w', encoding='utf-8') as _:
            _.write(text)
        return self.parser.parse(path)

    def test_basic(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 2)
        self.assertEqual(all_sources['index.markdown'],
                         ['section.markdown'])

    def test_nesting(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown\n'
               '\t\tsubsection.markdown')

        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 3)
        self.assertEqual(all_sources['index.markdown'],
                         ['section.markdown'])
        self.assertEqual(all_sources['section.markdown'],
                         ['subsection.markdown'])

    def test_unnesting(self):
        inp = (u'index.markdown\n'
               '\tsection1.markdown\n'
               '\t\tsubsection.markdown\n'
               '\tsection2.markdown')

        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 4)
        self.assertEqual(all_sources['index.markdown'],
                         ['section1.markdown', 'section2.markdown'])

    def test_empty_lines(self):
        inp = (u'index.markdown\n'
               '\n'
               '\tsection.markdown')
        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 2)
        self.assertEqual(all_sources['index.markdown'],
                         ['section.markdown'])

    def test_quoting(self):
        inp = (u'index.markdown\n'
               '\t" section with spaces.markdown "')
        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 2)
        self.assertEqual(all_sources['index.markdown'],
                         [' section with spaces.markdown '])

    def test_invalid_indentation(self):
        inp = (u'index.markdown\n'
               '\tsection1.markdown\n'
               '\tsection2.markdown\n'
               '\t invalid.markdown\n'
               '\tsection3.markdown\n'
               '\tsection4.markdown\n'
               '\tsection5.markdown')
        with self.assertRaises(IndentError) as cm:
            self.parse(inp)
        self.assertEqual(cm.exception.lineno, 3)
        self.assertEqual(cm.exception.column, 9)
        self.assertEqual(cm.exception.filename,
                         os.path.join(self.__tmp_dir, 'sitemap.txt'))

    def test_duplicate_file(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown\n'
               '\tsection.markdown\n')

        with self.assertRaises(SitemapDuplicateError) as cm:
            self.parse(inp)
        self.assertEqual(cm.exception.lineno, 2)
        self.assertEqual(cm.exception.column, 9)

    def test_multiple_roots(self):
        inp = (u'index.markdown\n'
               'other_index.markdown\n')

        with self.assertRaises(SitemapError) as cm:
            self.parse(inp)
        self.assertEqual(cm.exception.lineno, 1)
        self.assertEqual(cm.exception.column, 0)


class TestStandaloneParser(unittest.TestCase):

    def setUp(self):
        self.doc_database = DocDatabase()
        self.link_resolver = LinkResolver(self.doc_database)

    def test_symbol_lists(self):
        inp = (u'### A title\n'
               '\n'
               'A paragraph with *an inline*\n'
               '\n'
               '* [A link with no url]()\n'
               '* [A_link_with_a_url](test.com)\n'
               '* [A link followed by stuff](test.com) stuff\n')

        ast = cmark.hotdoc_to_ast(inp, None)

        # The empty link should have been filtered out
        self.assertEqual(
            cmark.ast_to_html(ast, self.link_resolver),
            (u'<h3>A title</h3>\n'
             '<p>A paragraph with <em>an inline</em></p>\n'
             '<ul>\n'
             '<li><a href="test.com">A_link_with_a_url</a></li>\n'
             '<li><a href="test.com">A link followed by stuff</a> stuff</li>\n'
             '</ul>\n'))

        # And collected in the symbol names
        self.assertListEqual(
            cmark.symbol_names_in_ast(ast),
            [u'A link with no url'])


class TestExtension(Extension):
    extension_name = 'test-extension'
    argument_prefix = 'test'

    def __init__(self, doc_repo):
        self.formatters = {'html': None}
        super(TestExtension, self).__init__(doc_repo)

    def setup(self):
        stale, _ = self.get_stale_files(self.sources)
        for source in stale:
            with open(source, 'r') as _:
                for l in _.readlines():
                    l = l.strip()
                    self.get_or_create_symbol(
                        FunctionSymbol,
                        unique_name=l, filename=source)

    def _get_all_sources(self):
        return self.sources


class TestDocTree(unittest.TestCase):
    def setUp(self):
        here = os.path.dirname(__file__)
        self.__md_dir = os.path.abspath(os.path.join(
            here, 'tmp-markdown-files'))
        self.__priv_dir = os.path.abspath(os.path.join(
            here, 'tmp-private'))
        self.__src_dir = os.path.abspath(os.path.join(
            here, 'tmp-src-files'))
        self.__remove_tmp_dirs()
        os.mkdir(self.__md_dir)
        os.mkdir(self.__priv_dir)
        os.mkdir(self.__src_dir)
        os.mkdir(self.get_generated_doc_folder())
        self.include_paths = OrderedSet([self.__md_dir])
        self.include_paths.add(self.get_generated_doc_folder())

        # Using the real doc database is too costly, tests should be lightning
        # fast (and they are)
        self.doc_database = DocDatabase()
        self.doc_database.setup(self.__priv_dir)

        self.change_tracker = ChangeTracker()

        self.sitemap_parser = SitemapParser()

        self.test_ext = TestExtension(self)

    def tearDown(self):
        self.__remove_tmp_dirs()
        del self.test_ext

    def get_generated_doc_folder(self):
        return os.path.join(self.__priv_dir, 'generated')

    def get_base_doc_folder(self):
        return self.__md_dir

    def get_private_folder(self):
        return self.__priv_dir

    def __parse_sitemap(self, text):
        path = os.path.join(self.__md_dir, 'sitemap.txt')
        with io.open(path, 'w', encoding='utf-8') as _:
            _.write(text)
        return self.sitemap_parser.parse(path)

    def __create_md_file(self, name, contents):
        with open(os.path.join(self.__md_dir, name), 'w') as _:
            _.write(contents)

    def __create_src_file(self, name, symbols):
        path = os.path.join(self.__md_dir, name)
        with open(path, 'w') as _:
            for symbol in symbols:
                _.write('%s\n' % symbol)
        return path

    def __remove_tmp_dirs(self):
        shutil.rmtree(self.__md_dir, ignore_errors=True)
        shutil.rmtree(self.__priv_dir, ignore_errors=True)
        shutil.rmtree(self.__src_dir, ignore_errors=True)
        shutil.rmtree(self.get_generated_doc_folder(), ignore_errors=True)

    def test_basic(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        sitemap = self.__parse_sitemap(inp)
        self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'section.markdown',
            (u'# My section\n'))

        doc_tree = DocTree(self.__priv_dir, self.include_paths)
        doc_tree.parse_sitemap(self.change_tracker, sitemap)

        pages = doc_tree.get_pages()

        # We do not care about ordering
        self.assertSetEqual(
            set(pages.keys()),
            set([u'index.markdown',
                 u'section.markdown']))

    def test_basic_incremental(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        sitemap = self.__parse_sitemap(inp)
        self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'section.markdown',
            (u'# My section\n'))

        doc_tree = DocTree(self.__priv_dir, self.include_paths)
        doc_tree.parse_sitemap(self.change_tracker, sitemap)

        # Building from scratch, all pages are stale
        self.assertSetEqual(
            set(doc_tree.get_stale_pages()),
            set([u'index.markdown',
                 u'section.markdown']))

        doc_tree.persist()

        doc_tree = DocTree(self.__priv_dir, self.include_paths)
        doc_tree.parse_sitemap(self.change_tracker, sitemap)

        # Nothing changed, no page is stale
        self.assertSetEqual(
            set(doc_tree.get_stale_pages()),
            set({}))

        # But we still have our pages
        self.assertSetEqual(
            set(doc_tree.get_pages()),
            set([u'index.markdown',
                 u'section.markdown']))

        touch(os.path.join(self.__md_dir, u'section.markdown'))

        doc_tree = DocTree(self.__priv_dir, self.include_paths)
        doc_tree.parse_sitemap(self.change_tracker, sitemap)

        self.assertSetEqual(
            set(doc_tree.get_stale_pages()),
            set([u'section.markdown']))

    def __assert_extension_names(self, doc_tree, name_map):
        pages = doc_tree.get_pages()
        for name, ext_name in name_map.items():
            page = pages[name]
            self.assertEqual(ext_name, page.extension_name)

    def __assert_stale(self, doc_tree, expected_stale):
        stale_pages = doc_tree.get_stale_pages()
        for pagename in expected_stale:
            self.assertIn(pagename, stale_pages)
            stale_pages.pop(pagename)
        self.assertEqual(len(stale_pages), 0)

    def __create_test_layout(self):
        inp = (u'index.markdown\n'
               '\ttest-index\n'
               '\t\ttest-section.markdown\n'
               '\t\t\tsource_a.test\n'
               '\t\tpage_x.markdown\n'
               '\t\tpage_y.markdown\n'
               '\tcore_page.markdown\n')

        sources = []

        sources.append(self.__create_src_file(
            'source_a.test',
            ['symbol_1',
             'symbol_2']))

        sources.append(self.__create_src_file(
            'source_b.test',
            ['symbol_3',
             'symbol_4']))

        self.test_ext.index = 'test-index.markdown'
        self.test_ext.sources = sources
        self.test_ext.setup()

        sitemap = self.__parse_sitemap(inp)

        self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'core_page.markdown',
            (u'# My non-extension page\n'))
        self.__create_md_file(
            'test-index.markdown',
            (u'# My test index\n'))
        self.__create_md_file(
            'test-section.markdown',
            (u'# My test section\n'
             '\n'
             'Linking to [a generated page](source_a.test)\n'))
        self.__create_md_file(
            'page_x.markdown',
            (u'# Page X\n'
             '\n'
             '* [symbol_3]()\n'))
        self.__create_md_file(
            'page_y.markdown',
            (u'# Page Y\n'))

        doc_tree = DocTree(self.__priv_dir, self.include_paths)
        doc_tree.parse_sitemap(self.change_tracker, sitemap)

        return doc_tree

    def test_extension_basic(self):
        doc_tree = self.__create_test_layout()
        self.__assert_extension_names(
            doc_tree,
            {u'index.markdown': 'core',
             u'test-index': 'test-extension',
             u'test-section.markdown': 'test-extension',
             u'source_a.test': 'test-extension',
             u'source_b.test': 'test-extension',
             u'page_x.markdown': 'test-extension',
             u'page_y.markdown': 'test-extension',
             u'core_page.markdown': 'core'})

        all_pages = doc_tree.get_pages()
        self.assertEqual(len(all_pages), 8)
        self.__assert_stale(doc_tree, all_pages)
        self.assertNotIn('source_a.test', all_pages['test-index'].subpages)
        self.assertIn('source_a.test',
                      all_pages['test-section.markdown'].subpages)

    def test_extension_override(self):
        self.__create_md_file(
            'source_a.test.markdown',
            (u'# My override\n'))
        doc_tree = self.__create_test_layout()
        page = doc_tree.get_pages()['source_a.test']
        print cmark.ast_to_html(page.ast, None)
        print page.symbol_names
