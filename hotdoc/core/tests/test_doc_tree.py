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

from hotdoc.core.filesystem import ChangeTracker
from hotdoc.core.database import Database
from hotdoc.core.project import CoreExtension
from hotdoc.core.symbols import FunctionSymbol
from hotdoc.core.links import LinkResolver
from hotdoc.parsers.sitemap import SitemapParser
from hotdoc.parsers import cmark
from hotdoc.core.tree import Tree
from hotdoc.core.extension import Extension
from hotdoc.utils.utils import OrderedSet, touch
from hotdoc.core.config import Config


class TestExtension(Extension):
    extension_name = 'test-extension'
    argument_prefix = 'test'

    def __init__(self, app, project):
        super(TestExtension, self).__init__(app, project)

    # pylint: disable=arguments-differ
    def setup(self, smart=True):
        super(TestExtension, self).setup()
        self.smart_index = smart
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


class TestTree(unittest.TestCase):
    def setUp(self):
        here = os.path.dirname(__file__)
        self.__md_dir = os.path.abspath(os.path.join(
            here, 'tmp-markdown-files'))
        self.private_folder = os.path.abspath(os.path.join(
            here, 'tmp-private'))
        self.__src_dir = os.path.abspath(os.path.join(
            here, 'tmp-src-files'))
        self.__output_dir = os.path.abspath(os.path.join(
            here, 'tmp-output'))
        self.__remove_tmp_dirs()
        os.mkdir(self.__md_dir)
        os.mkdir(self.private_folder)
        os.mkdir(self.__src_dir)
        os.mkdir(self.get_generated_doc_folder())
        self.include_paths = OrderedSet([self.__md_dir])
        self.include_paths.add(self.get_generated_doc_folder())

        # Using the real doc database is too costly, tests should be lightning
        # fast (and they are)
        self.database = Database()
        self.database.setup(self.private_folder)
        self.link_resolver = LinkResolver(self.database)

        self.change_tracker = ChangeTracker()

        self.sitemap_parser = SitemapParser()

        self.project_name = 'test-project'
        self.sanitized_name = 'test-project-0.1'
        self.incremental = False

        self.tree = Tree(self, self)

        self.test_ext = TestExtension(self, self)
        self.core_ext = CoreExtension(self, self)

        cfg = Config()

        self.test_ext.parse_config(cfg)
        self.core_ext.parse_config(cfg)
        self.subprojects = {}
        self.is_toplevel = True

    def tearDown(self):
        self.__remove_tmp_dirs()
        del self.test_ext
        del self.core_ext

    def get_generated_doc_folder(self):
        return os.path.join(self.private_folder, 'generated')

    def get_base_doc_folder(self):
        return self.__md_dir

    def get_private_folder(self):
        return self.private_folder

    def __parse_sitemap(self, text):
        path = os.path.join(self.__md_dir, 'sitemap.txt')
        with io.open(path, 'w', encoding='utf-8') as _:
            _.write(text)
        return self.sitemap_parser.parse(path)

    def __create_md_file(self, name, contents):
        path = os.path.join(self.__md_dir, name)
        with open(path, 'w') as _:
            _.write(contents)

        # Just making sure we don't hit a race condition,
        # in real world situations it is assumed users
        # will not update source files twice in the same
        # microsecond
        touch(path)

    def __create_src_file(self, name, symbols):
        path = os.path.join(self.__md_dir, name)
        with open(path, 'w') as _:
            for symbol in symbols:
                _.write('%s\n' % symbol)

        # Just making sure we don't hit a race condition,
        # in real world situations it is assumed users
        # will not update source files twice in the same
        # microsecond
        touch(path)

        return path

    def __remove_src_file(self, name):
        path = os.path.join(self.__md_dir, name)
        os.unlink(path)

    def __remove_md_file(self, name):
        path = os.path.join(self.__md_dir, name)
        os.unlink(path)

    def __touch_src_file(self, name):
        path = os.path.join(self.__md_dir, name)
        touch(path)

    def __remove_tmp_dirs(self):
        shutil.rmtree(self.__md_dir, ignore_errors=True)
        shutil.rmtree(self.private_folder, ignore_errors=True)
        shutil.rmtree(self.__src_dir, ignore_errors=True)
        shutil.rmtree(self.__output_dir, ignore_errors=True)
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

        self.tree.parse_sitemap(sitemap)

        pages = self.tree.get_pages()

        # We do not care about ordering
        self.assertSetEqual(
            set(pages.keys()),
            set([u'index.markdown',
                 u'section.markdown']))

        index = pages.get('index.markdown')
        self.assertEqual(index.title, u'My documentation')

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

        self.tree.parse_sitemap(sitemap)

        # Building from scratch, all pages are stale
        self.assertSetEqual(
            set(self.tree.get_stale_pages()),
            set([u'index.markdown',
                 u'section.markdown']))

        self.tree.persist()

        self.incremental = True
        self.tree = Tree(self, self)
        self.tree.parse_sitemap(sitemap)

        # Nothing changed, no page is stale
        self.assertSetEqual(
            set(self.tree.get_stale_pages()),
            set({}))

        # But we still have our pages
        self.assertSetEqual(
            set(self.tree.get_pages()),
            set([u'index.markdown',
                 u'section.markdown']))

        touch(os.path.join(self.__md_dir, u'section.markdown'))

        self.tree = Tree(self, self)
        self.tree.parse_sitemap(sitemap)

        self.assertSetEqual(
            set(self.tree.get_stale_pages()),
            set([u'section.markdown']))

    def __assert_extension_names(self, tree, name_map):
        pages = tree.get_pages()
        for name, ext_name in list(name_map.items()):
            page = pages[name]
            self.assertEqual(ext_name, page.extension_name)

    def __assert_stale(self, expected_stale):
        stale_pages = self.tree.get_stale_pages()
        for pagename in expected_stale:
            self.assertIn(pagename, stale_pages)
            stale_pages.pop(pagename)
        self.assertEqual(len(stale_pages), 0)

    def __create_test_layout(self, with_ext_index=True, sitemap=None):
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

        sources = []

        sources.append(self.__create_src_file(
            'source_a.test',
            ['symbol_1',
             'symbol_2']))

        sources.append(self.__create_src_file(
            'source_b.test',
            ['symbol_3',
             'symbol_4']))

        if with_ext_index:
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
        if with_ext_index:
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
            (u'---\n'
             'symbols: [symbol_3]\n'
             '...\n'
             '# Page X\n'))
        self.__create_md_file(
            'page_y.markdown',
            (u'# Page Y\n'))

        self.tree.parse_sitemap(sitemap)

        return sitemap

    def __update_test_layout(self, sitemap):
        self.test_ext.reset()
        self.tree = Tree(self, self)
        self.test_ext.setup()
        self.tree.parse_sitemap(sitemap)

    def test_extension_basic(self):
        _ = self.__create_test_layout()
        self.__assert_extension_names(
            self.tree,
            {u'index.markdown': 'core',
             u'test-index': 'test-extension',
             u'test-section.markdown': 'test-extension',
             u'source_a.test': 'test-extension',
             u'source_b.test': 'test-extension',
             u'page_x.markdown': 'test-extension',
             u'page_y.markdown': 'test-extension',
             u'core_page.markdown': 'core'})

        all_pages = self.tree.get_pages()
        self.assertEqual(len(all_pages), 8)
        self.__assert_stale(all_pages)
        self.assertNotIn('source_a.test', all_pages['test-index'].subpages)
        self.assertIn('source_a.test',
                      all_pages['test-section.markdown'].subpages)

    def test_extension_override(self):
        self.__create_md_file(
            'source_a.test.markdown',
            (u'# My override\n'))
        _ = self.__create_test_layout()
        page = self.tree.get_pages()['source_a.test']

        self.assertEqual(
            page.symbol_names,
            OrderedSet(['symbol_1',
                        'symbol_2']))

        self.assertEqual(
            os.path.basename(page.source_file),
            'source_a.test.markdown')

        out, _ = cmark.ast_to_html(page.ast, None)

        self.assertEqual(
            out,
            u'<h1>My override</h1>\n')

    def test_no_extension_index_override(self):
        _ = self.__create_test_layout(with_ext_index=False)
        ext_index = self.tree.get_pages()['test-index']
        self.assertEqual(ext_index.generated, True)
        self.assertEqual(len(ext_index.subpages), 4)

    def test_parse_yaml(self):
        inp = (u'index.markdown\n')
        sitemap = self.__parse_sitemap(inp)
        self.__create_md_file(
            'index.markdown',
            (u'---\n'
             'title: A random title\n'
             'symbols: [symbol_1, symbol_2]\n'
             '...\n'
             '# My documentation\n'))

        self.tree.parse_sitemap(sitemap)

        pages = self.tree.get_pages()
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
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        sitemap = self.__parse_sitemap(inp)
        self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'section.markdown',
            (u'# My section\n'
             '\n'
             '[](index.markdown)\n'))

        self.tree.parse_sitemap(sitemap)
        self.tree.resolve_symbols(self.database, self.link_resolver)
        self.tree.format(
            self.link_resolver, self.__output_dir,
            {self.core_ext.extension_name: self.core_ext})

        pages = self.tree.get_pages()
        page = pages.get('section.markdown')
        self.assertEqual(
            page.formatted_contents,
            u'<h1>My section</h1>\n'
            '<p><a href="index.html">My documentation</a></p>\n')

    def test_labeled_link_resolution(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        sitemap = self.__parse_sitemap(inp)
        self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'section.markdown',
            (u'# My section\n'
             '\n'
             '[a label](index.markdown)\n'))

        self.tree.parse_sitemap(sitemap)
        self.tree.resolve_symbols(self.database, self.link_resolver)
        self.tree.format(
            self.link_resolver, self.__output_dir,
            {self.core_ext.extension_name: self.core_ext})

        pages = self.tree.get_pages()
        page = pages.get('section.markdown')
        self.assertEqual(
            page.formatted_contents,
            u'<h1>My section</h1>\n'
            '<p><a href="index.html">a label</a></p>\n')

    def test_anchored_link_resolution(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        sitemap = self.__parse_sitemap(inp)
        self.__create_md_file(
            'index.markdown',
            (u'# My documentation\n'))
        self.__create_md_file(
            'section.markdown',
            (u'# My section\n'
             '\n'
             '[](index.markdown#subsection)\n'))

        self.tree.parse_sitemap(sitemap)
        self.tree.resolve_symbols(self.database, self.link_resolver)
        self.tree.format(
            self.link_resolver, self.__output_dir,
            {self.core_ext.extension_name: self.core_ext})

        pages = self.tree.get_pages()
        page = pages.get('section.markdown')
        self.assertEqual(
            page.formatted_contents,
            u'<h1>My section</h1>\n'
            '<p><a href="index.html#subsection">My documentation</a></p>\n')

    # pylint: disable=too-many-statements
    def test_extension_incremental(self):
        sitemap = self.__create_test_layout()
        self.tree.persist()

        self.incremental = True

        # Here we touch source_a.test, as its symbols were
        # all contained in a generated page, only that page
        # should now be stale
        self.__touch_src_file('source_a.test')
        self.__update_test_layout(sitemap)
        self.__assert_stale(set(['source_a.test']))
        self.tree.persist()

        # We now touch source_b.test, which symbols are contained
        # both in a generated page and a user-provided one.
        # We expect both pages to be stale
        self.__touch_src_file('source_b.test')
        self.__update_test_layout(sitemap)
        self.__assert_stale(set(['source_b.test',
                                 'page_x.markdown']))
        self.tree.persist()

        # This one is trickier: we unlist symbol_3 from
        # page_x, which means the symbol should now be
        # documented in the generated page for source_b.test.
        # We expect both pages to be stale, and make sure
        # they contain the right symbols
        self.__create_md_file(
            'page_x.markdown',
            (u'# Page X\n'))
        self.__update_test_layout(sitemap)
        self.__assert_stale(set(['source_b.test',
                                 'page_x.markdown']))

        page_x = self.tree.get_pages()['page_x.markdown']
        self.assertEqual(page_x.symbol_names, OrderedSet())

        source_b_page = self.tree.get_pages()['source_b.test']
        self.assertEqual(
            source_b_page.symbol_names,
            OrderedSet(['symbol_4', 'symbol_3']))

        self.tree.persist()

        # Let's make sure the opposite use case works as well,
        # we relocate symbol_3 in page_x , both page_x and
        # the generated page for source_b.test should be stale
        # and the symbols should be back to their original
        # layout.
        self.__create_md_file(
            'page_x.markdown',
            (u'---\n'
             'symbols: [symbol_3]\n'
             '...\n'
             '# Page X\n'))

        self.__update_test_layout(sitemap)
        self.__assert_stale(set(['source_b.test',
                                 'page_x.markdown']))

        page_x = self.tree.get_pages()['page_x.markdown']
        self.assertEqual(page_x.symbol_names, OrderedSet(['symbol_3']))

        source_b_page = self.tree.get_pages()['source_b.test']
        self.assertEqual(
            source_b_page.symbol_names,
            OrderedSet(['symbol_4']))

        self.tree.persist()

        # We now move the definition of symbol_3 to source_a.test,
        # we thus expect the generated page for source_a.test to be
        # stale because its source changed, same for source_b.test,
        # and page_x.markdown should be stale as well because the
        # definition of symbol_3 may have changed. The final
        # symbol layout should not have changed however.
        self.__create_src_file(
            'source_a.test',
            ['symbol_1',
             'symbol_2',
             'symbol_3'])
        self.__create_src_file(
            'source_b.test',
            ['symbol_4'])
        self.__update_test_layout(sitemap)

        self.__assert_stale(set(['source_a.test',
                                 'source_b.test',
                                 'page_x.markdown']))

        page_x = self.tree.get_pages()['page_x.markdown']
        self.assertEqual(page_x.symbol_names, OrderedSet(['symbol_3']))

        source_b_page = self.tree.get_pages()['source_b.test']
        self.assertEqual(
            source_b_page.symbol_names,
            OrderedSet(['symbol_4']))

        source_a_page = self.tree.get_pages()['source_a.test']
        self.assertEqual(
            source_a_page.symbol_names,
            OrderedSet(['symbol_1',
                        'symbol_2']))

        self.tree.persist()

        # And we rollback again
        self.__create_src_file(
            'source_a.test',
            ['symbol_1',
             'symbol_2'])
        self.__create_src_file(
            'source_b.test',
            ['symbol_3',
             'symbol_4'])
        self.__update_test_layout(sitemap)

        self.__assert_stale(set(['source_a.test',
                                 'source_b.test',
                                 'page_x.markdown']))

        page_x = self.tree.get_pages()['page_x.markdown']
        self.assertEqual(page_x.symbol_names, OrderedSet(['symbol_3']))

        source_b_page = self.tree.get_pages()['source_b.test']
        self.assertEqual(
            source_b_page.symbol_names,
            OrderedSet(['symbol_4']))

        source_a_page = self.tree.get_pages()['source_a.test']
        self.assertEqual(
            source_a_page.symbol_names,
            OrderedSet(['symbol_1',
                        'symbol_2']))

        self.tree.persist()

        # Now we'll try removing page_x altogether
        self.__remove_md_file('page_x.markdown')
        inp = (u'index.markdown\n'
               '\ttest-index\n'
               '\t\ttest-section.markdown\n'
               '\t\t\tsource_a.test\n'
               '\t\tpage_y.markdown\n'
               '\tcore_page.markdown\n')

        new_sitemap = self.__parse_sitemap(inp)
        self.__update_test_layout(new_sitemap)
        self.__assert_stale(set(['source_b.test']))
        source_b_page = self.tree.get_pages()['source_b.test']
        self.assertEqual(
            source_b_page.symbol_names,
            OrderedSet(['symbol_4', 'symbol_3']))
        self.tree.persist()

        # And rollback again
        self.__create_md_file(
            'page_x.markdown',
            (u'---\n'
             'symbols: [symbol_3]\n'
             '...\n'
             '# Page X\n'))
        self.__update_test_layout(sitemap)
        self.__assert_stale(set(['page_x.markdown',
                                 'source_b.test']))

        page_x = self.tree.get_pages()['page_x.markdown']
        self.assertEqual(page_x.symbol_names, OrderedSet(['symbol_3']))

        source_b_page = self.tree.get_pages()['source_b.test']
        self.assertEqual(
            source_b_page.symbol_names,
            OrderedSet(['symbol_4']))

        self.tree.persist()

    def test_index_override_incremental(self):
        sitemap = self.__create_test_layout()
        self.tree.persist()
        index_page = self.tree.get_pages()['test-index']
        self.assertIn('source_b.test', index_page.subpages)

        self.incremental = True

        self.__touch_src_file('test-index.markdown')
        self.__update_test_layout(sitemap)
        index_page = self.tree.get_pages()['test-index']
        self.assertIn('source_b.test', index_page.subpages)
        self.tree.persist()

    def test_extension_index_only(self):
        inp = (u'test-index\n'
               '\ttest-section.markdown\n')
        self.test_ext.setup()
        sitemap = self.__parse_sitemap(inp)
        self.__create_md_file(
            'test-section.markdown',
            u'# My test section\n')
        self.tree.parse_sitemap(sitemap)
        self.__assert_extension_names(
            self.tree,
            {u'test-index': 'test-extension',
             u'test-section.markdown': 'test-extension'})

    def test_extension_auto_sorted_override(self):
        self.__create_md_file(
            'source_b.test.markdown',
            (u'---\nauto-sort: true\n...\n# My override\n'))
        sitemap = (u'index.markdown\n'
                   '\ttest-index\n'
                   '\t\ttest-section.markdown\n'
                   '\t\t\tsource_b.test\n'
                   '\t\t\tsource_a.test\n'
                   '\t\tpage_x.markdown\n'
                   '\t\tpage_y.markdown\n'
                   '\tcore_page.markdown\n')
        _ = self.__create_test_layout(sitemap=sitemap)
        pages = self.tree.get_pages()
        self.assertTrue(pages['source_a.test'].pre_sorted)
        self.assertFalse(pages['source_b.test'].pre_sorted)

        self.__create_md_file(
            'source_b.test.markdown',
            (u'# My override\n'))
        sitemap = (u'index.markdown\n'
                   '\ttest-index\n'
                   '\t\ttest-section.markdown\n'
                   '\t\t\tsource_b.test\n'
                   '\t\t\tsource_a.test\n'
                   '\t\tpage_x.markdown\n'
                   '\t\tpage_y.markdown\n'
                   '\tcore_page.markdown\n')
        _ = self.__create_test_layout(sitemap=sitemap)
        pages = self.tree.get_pages()
        self.assertTrue(pages['source_a.test'].pre_sorted)
        self.assertTrue(pages['source_b.test'].pre_sorted)

    def test_extension_implicit_override(self):
        self.__create_md_file(
            'source_b.test.markdown',
            (u'---\nsymbols:\n  - symbol_2\n...\n# My override\n'))
        _ = self.__create_test_layout()

        source_b = self.tree.get_pages()['source_b.test']
        self.assertEqual(
            os.path.basename(source_b.source_file),
            'source_b.test.markdown')
        self.assertEqual(source_b.symbol_names, ['symbol_2', 'symbol_4'])

        source_a = self.tree.get_pages()['source_a.test']
        self.assertEqual(source_a.symbol_names, ['symbol_1'])

        out, _ = cmark.ast_to_html(source_b.ast, None)

        self.assertEqual(
            out,
            u'<h1>My override</h1>\n')
