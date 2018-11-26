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

from hotdoc.core.symbols import ClassSymbol, FunctionSymbol
from hotdoc.parsers import cmark
from hotdoc.core.extension import Extension
from hotdoc.utils.utils import OrderedSet
from hotdoc.utils.loggable import Logger
from hotdoc.core.config import Config
from hotdoc.run_hotdoc import Application
from hotdoc.core.comment import Comment


class TestExtension(Extension):
    extension_name = 'test-extension'
    argument_prefix = 'test'
    symbols = []
    comments = []

    # pylint: disable=arguments-differ
    def setup(self):
        super(TestExtension, self).setup()
        for args, kwargs in TestExtension.symbols:
            self.create_symbol(*args, **kwargs)

        for comment in TestExtension.comments:
            self.add_comment(comment)

    def _get_all_sources(self):
        return self.sources

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('Test extension', 'A test extension')
        TestExtension.add_index_argument(group)
        TestExtension.add_sources_argument(group, add_root_paths=True)


class TestTree(unittest.TestCase):
    def setUp(self):
        here = os.path.dirname(__file__)
        self.__test_dir = os.path.abspath(os.path.join(here, 'testdir'))
        self.__md_dir = os.path.join(self.__test_dir, 'tmp-markdown-files')
        self.private_folder = os.path.join(self.__test_dir, 'tmp-private')
        self.__src_dir = os.path.join(self.__test_dir, 'tmp-src-files')
        self.__output_dir = os.path.join(self.__test_dir, 'tmp-output')
        self.__remove_tmp_dirs()
        os.mkdir(self.__test_dir)
        os.mkdir(self.__md_dir)
        os.mkdir(self.private_folder)
        os.mkdir(self.__src_dir)

        self.app = Application((TestExtension,))

        Logger.fatal_warnings = True

    def tearDown(self):
        #self.__remove_tmp_dirs()
        TestExtension.symbols = []
        TestExtension.comments = []
        Logger.fatal_warnings = False

    def __write_sitemap(self, text):
        path = os.path.join(self.__md_dir, 'sitemap.txt')
        with io.open(path, 'w', encoding='utf-8') as _:
            _.write(text)
        return path

    def __create_md_file(self, name, contents):
        path = os.path.join(self.__md_dir, name)
        with open(path, 'w') as _:
            _.write(contents)
        return path

    def __create_src_file(self, name, symbols):
        path = os.path.join(self.__src_dir, name)
        if os.path.dirname(name):
            os.makedirs(os.path.join(self.__src_dir, os.path.dirname(name)))
        with open(path, 'w') as _:
            for symbol in symbols:
                _.write('%s\n' % symbol)

        return path

    def __remove_tmp_dirs(self):
        shutil.rmtree(self.__test_dir, ignore_errors=True)

    def __make_config(self, conf):
        return Config(conf_file=os.path.join(self.__test_dir, 'hotdoc.json'),
                      json_conf=conf)

    def test_basic(self):
        conf = {'project_name': 'test',
                'project_version': '1.0'}
        self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        conf['index'] = self.__create_md_file(
            'section.markdown',
            (u'# My section\n'))
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        conf['sitemap'] = self.__write_sitemap(inp)
        conf = self.__make_config(conf)
        self.app.parse_config(conf)
        self.app.run()

        pages = self.app.project.tree.get_pages()

        self.assertSetEqual(
            set(pages.keys()),
            set([u'index.markdown',
                 u'section.markdown']))

        index = pages.get('index.markdown')
        self.assertEqual(index.title, u'My documentation')

    def __assert_extension_names(self, tree, name_map):
        pages = tree.get_pages()
        for name, ext_name in list(name_map.items()):
            page = pages[name]
            self.assertEqual(ext_name, page.extension_name)

    # pylint: disable=too-many-arguments
    def __create_test_layout(self, with_ext_index=True, sitemap=None,
                             symbols=None, source_roots=None, comments=None,
                             output=None):
        conf = {'project_name': 'test',
                'project_version': '1.0'}
        if not sitemap:
            inp = (u'index.markdown\n'
                   '\ttest-index\n'
                   '\t\ttest-section.markdown\n'
                   '\t\t\tsource_a.test\n'
                   '\t\tpage_x.markdown\n'
                   '\t\tpage_y.markdown\n'
                   '\tcore_page.markdown\n')
        else:
            inp = sitemap

        if symbols is None:
            TestExtension.symbols = [
                (
                    [FunctionSymbol],
                    {
                        'unique_name': 'symbol_1',
                        'filename': 'source_a.test'
                    }
                ),
                (
                    [FunctionSymbol],
                    {
                        'unique_name': 'symbol_2',
                        'filename': 'source_a.test'
                    }
                ),
                (
                    [FunctionSymbol],
                    {
                        'unique_name': 'symbol_3',
                        'filename': 'source_b.test'
                    }
                ),
                (
                    [FunctionSymbol],
                    {
                        'unique_name': 'symbol_4',
                        'filename': 'source_b.test'
                    }
                ),
            ]
        else:
            TestExtension.symbols = symbols

        if comments is not None:
            TestExtension.comments = comments

        conf['test_sources'] = []
        all_src_files = set()
        for _, kwargs in TestExtension.symbols:
            fname = kwargs.get('filename')
            if fname is not None:
                if fname not in all_src_files:
                    conf['test_sources'].append(self.__create_src_file(fname, []))
                    all_src_files.add(fname)
                kwargs['filename'] = os.path.join(self.__src_dir, fname)

        if source_roots:
            conf['test_source_roots'] = source_roots

        if output:
            conf['output'] = output

        conf['index'] = self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'core_page.markdown',
            (u'# My non-extension page\n'))
        self.__create_md_file(
            'test-section.markdown',
            (u'# My test section\n'
             '\n'
             'Linking to [a generated page](source_a.test)\n'))
        self.__create_md_file(
            'page_x.markdown',
            (u'---\n'
             'symbols: [symbol_3]\n'
             '...\n'
             '# Page X\n'))
        self.__create_md_file(
            'page_y.markdown',
            (u'# Page Y\n'))

        if with_ext_index:
            conf['test-index'] = self.__create_md_file(
                'test-index.markdown',
                (u'# My test index\n'))

        conf['sitemap'] = self.__write_sitemap(inp)

        conf = self.__make_config(conf)

        self.app.parse_config(conf)
        self.app.run()

    def test_extension_basic(self):
        self.__create_test_layout()
        self.__assert_extension_names(
            self.app.project.tree,
            {u'index.markdown': 'core',
             u'test-index': 'test-extension',
             u'test-section.markdown': 'test-extension',
             u'source_a.test': 'test-extension',
             u'source_b.test': 'test-extension',
             u'page_x.markdown': 'test-extension',
             u'page_y.markdown': 'test-extension',
             u'core_page.markdown': 'core'})

        all_pages = self.app.project.tree.get_pages()
        self.assertEqual(len(all_pages), 8)
        self.assertNotIn('source_a.test', all_pages['test-index'].subpages)
        self.assertIn('source_a.test',
                      all_pages['test-section.markdown'].subpages)

    def test_no_extension_index_override(self):
        self.__create_test_layout(with_ext_index=False)
        ext_index = self.app.project.tree.get_pages()['test-index']
        self.assertEqual(ext_index.generated, True)
        self.assertEqual(len(ext_index.subpages), 4)

    def test_parse_yaml(self):
        conf = {'project_name': 'test',
                'project_version': '1.0'}
        inp = (u'index.markdown\n')
        conf['sitemap'] = self.__write_sitemap(inp)
        conf['index'] = self.__create_md_file(
            'index.markdown',
            (u'---\n'
             'title: A random title\n'
             'symbols: [symbol_1, symbol_2]\n'
             '...\n'
             '# My documentation\n'))

        conf = self.__make_config(conf)
        self.app.parse_config(conf)
        self.app.run()

        pages = self.app.project.tree.get_pages()
        page = pages.get('index.markdown')

        out, _ = cmark.ast_to_html(page.ast, None)

        self.assertEqual(
            out,
            u'<h1>My documentation</h1>\n')

        self.assertEqual(page.title, u'A random title')

        self.assertEqual(
            page.symbol_names,
            OrderedSet(['symbol_1',
                        'symbol_2']))

    def test_empty_link_resolution(self):
        conf = {'project_name': 'test',
                'project_version': '1.0',
                'output': self.__output_dir}
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        conf['sitemap'] = self.__write_sitemap(inp)
        conf['index'] = self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'section.markdown',
            (u'# My section\n'
             '\n'
             '[](index.markdown)\n'))

        conf = self.__make_config(conf)
        self.app.parse_config(conf)
        self.app.run()

        pages = self.app.project.tree.get_pages()
        page = pages.get('section.markdown')
        self.assertEqual(
            page.formatted_contents,
            u'<h1>My section</h1>\n'
            '<p><a href="index.html">My documentation</a></p>\n')

    def test_labeled_link_resolution(self):
        conf = {'project_name': 'test',
                'project_version': '1.0',
                'output': self.__output_dir}
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        conf['sitemap'] = self.__write_sitemap(inp)
        conf['index'] = self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'section.markdown',
            (u'# My section\n'
             '\n'
             '[a label](index.markdown)\n'))

        conf = self.__make_config(conf)
        self.app.parse_config(conf)
        self.app.run()

        pages = self.app.project.tree.get_pages()
        page = pages.get('section.markdown')
        self.assertEqual(
            page.formatted_contents,
            u'<h1>My section</h1>\n'
            '<p><a href="index.html">a label</a></p>\n')

    def test_anchored_link_resolution(self):
        conf = {'project_name': 'test',
                'project_version': '1.0',
                'output': self.__output_dir}
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        conf['sitemap'] = self.__write_sitemap(inp)
        conf['index'] = self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'section.markdown',
            (u'# My section\n'
             '\n'
             '[](index.markdown#subsection)\n'))

        conf = self.__make_config(conf)
        self.app.parse_config(conf)
        self.app.run()

        pages = self.app.project.tree.get_pages()
        page = pages.get('section.markdown')
        self.assertEqual(
            page.formatted_contents,
            u'<h1>My section</h1>\n'
            '<p><a href="index.html#subsection">My documentation</a></p>\n')

    def test_extension_index_only(self):
        conf = {'project_name': 'test',
                'project_version': '1.0',
                'include_paths': [self.__md_dir]}
        inp = (u'test-index\n'
               '\ttest-section.markdown\n')
        conf['sitemap'] = self.__write_sitemap(inp)
        self.__create_md_file(
            'test-section.markdown',
            u'# My test section\n')

        conf = self.__make_config(conf)
        self.app.parse_config(conf)
        self.app.run()

        self.__assert_extension_names(
            self.app.project.tree,
            {u'test-index': 'test-extension',
             u'test-section.markdown': 'test-extension'})

    def test_extension_auto_sorted_override(self):
        sitemap = (u'index.markdown\n'
                   '\ttest-index\n'
                   '\t\ttest-section.markdown\n'
                   '\t\t\tsource_b.test\n'
                   '\t\t\tsource_a.test\n'
                   '\t\tpage_x.markdown\n'
                   '\t\tpage_y.markdown\n'
                   '\tcore_page.markdown\n')
        comments = [
            Comment(name='source_b.test',
                    filename=os.path.join(self.__src_dir, 'source_b.test'),
                    meta={'auto-sort': True}, toplevel=True),
        ]
        self.__create_test_layout(sitemap=sitemap, comments=comments)
        pages = self.app.project.tree.get_pages()
        self.assertTrue(pages['source_a.test'].pre_sorted)
        self.assertFalse(pages['source_b.test'].pre_sorted)

    def test_extension_file_include_dirs(self):
        sitemap = ('index.markdown\n'
                   '\ttest-index\n'
                   '\t\ttest-section.markdown\n'
                   '\t\t\tsource1.test\n'
                   '\t\t\tsource2.test\n')

        symbols = [
            (
                [FunctionSymbol],
                {
                    'unique_name': 'symbol_a',
                    'filename': 'a/source1.test'
                }
            ),
            (
                [FunctionSymbol],
                {
                    'unique_name': 'symbol_b',
                    'filename': 'b/source2.test'
                }
            ),
        ]

        self.__create_test_layout(
            sitemap=sitemap, symbols=symbols,
            source_roots=[os.path.join(self.__src_dir, 'a'),
                          os.path.join(self.__src_dir, 'b')])

        source1 = self.app.project.tree.get_pages()['source1.test']
        self.assertEqual(source1.symbol_names, ['symbol_a'])

        source2 = self.app.project.tree.get_pages()['source2.test']
        self.assertEqual(source2.symbol_names, ['symbol_b'])

    def test_multiple_toplevel_comments(self):
        sitemap = ('index.markdown\n'
                   '\ttest-index\n')

        symbols = [
            (
                [FunctionSymbol],
                {
                    'unique_name': 'symbol_a',
                    'filename': 'source1.test'
                }
            ),
            (
                [FunctionSymbol],
                {
                    'unique_name': 'symbol_b',
                    'filename': 'source1.test'
                }
            ),
            (
                [FunctionSymbol],
                {
                    'unique_name': 'symbol_c',
                    'filename': 'source1.test'
                }
            ),
        ]

        comments = [
            Comment(name='foo',
                    filename=os.path.join(self.__src_dir, 'source1.test'),
                    meta={'symbols': ['symbol_a']}, toplevel=True),
            Comment(name='bar',
                    filename=os.path.join(self.__src_dir, 'source1.test'),
                    meta={'symbols': ['symbol_b']}, toplevel=True),
        ]

        self.__create_test_layout(
            sitemap=sitemap, symbols=symbols, comments=comments,
            output=self.__output_dir)

        pages = self.app.project.tree.get_pages()

        self.assertEqual(len(pages), 4)
        self.assertIn('foo', pages)
        foo = pages['foo']
        self.assertEqual(foo.symbol_names, ['symbol_a', 'symbol_c'])

        self.assertIn('bar', pages)
        foo = pages['bar']
        self.assertEqual(foo.symbol_names, ['symbol_b'])

    def test_comment_relocation_basic(self):
        sitemap = ('index.markdown\n'
                   '\ttest-index\n')

        symbols = [
            (
                [FunctionSymbol],
                {
                    'unique_name': 'symbol_a',
                    'filename': 'source1.test'
                }
            ),
            (
                [FunctionSymbol],
                {
                    'unique_name': 'symbol_b',
                    'filename': 'source2.test'
                }
            ),
        ]

        # symbol_b should be documented in source1
        comments = [
            Comment(name='source1.test',
                    filename=os.path.join(self.__src_dir, 'source1.test'),
                    meta={'symbols': ['symbol_b']}, toplevel=True),
        ]

        self.__create_test_layout(
            sitemap=sitemap, symbols=symbols, comments=comments,
            output=self.__output_dir,
            source_roots=[os.path.join(self.__src_dir, 'a'),
                          os.path.join(self.__src_dir, 'b')])

        pages = self.app.project.tree.get_pages()
        self.assertEqual(len(pages), 3)
        self.assertIn('source1.test', pages)

        source1 = self.app.project.tree.get_pages()['source1.test']
        self.assertEqual(source1.symbol_names, ['symbol_a', 'symbol_b'])

        # source2 should not appear in the sitemap
        self.assertNotIn('source2.test', pages)

    def test_parented_symbols(self):
        sitemap = ('index.markdown\n'
                   '\ttest-index\n'
                   '\t\ttest-section.markdown\n')

        symbols = [
            (
                [ClassSymbol],
                {
                    'unique_name': 'symbol_a',
                    'filename': 'source1.test'
                }
            ),
            (
                [FunctionSymbol],
                {
                    'unique_name': 'symbol_b',
                    'filename': 'source2.test',
                    'parent_name': 'symbol_a',
                }
            ),
        ]

        self.__create_test_layout(
            sitemap=sitemap, symbols=symbols,
            source_roots=[os.path.join(self.__src_dir, 'a'),
                          os.path.join(self.__src_dir, 'b')])

        pages = self.app.project.tree.get_pages()
        self.assertIn('source1.test', pages)

        source1 = self.app.project.tree.get_pages()['source1.test']
        self.assertEqual(source1.symbol_names, ['symbol_a', 'symbol_b'])

        # source2 should not appear in the sitemap
        self.assertNotIn('source2.test', pages)
