# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
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

import os
import tempfile
import unittest
from hotdoc.parsers import cmark
from hotdoc.parsers.gtk_doc import GtkDocParser, GtkDocStringFormatter
from hotdoc.core.database import Database
from hotdoc.core.links import LinkResolver, Link
from hotdoc.core.exceptions import HotdocSourceException
from hotdoc.utils.loggable import Logger


class TestParser(unittest.TestCase):

    def setUp(self):
        self.database = Database(None)
        self.link_resolver = LinkResolver(self.database)
        self.link_resolver.add_link(Link("here.com", "foo", "foo"))

    def assertOutputs(self, inp, expected):
        ast, _ = cmark.gtkdoc_to_ast(inp, self.link_resolver)
        out = cmark.ast_to_html(ast, self.link_resolver)[0]
        self.assertEqual(out, expected)

    def test_basic(self):
        inp = u'a'
        self.assertOutputs(inp, u"<p>a</p>\n")

    def test_unicode(self):
        inp = u'”'
        self.assertOutputs(inp, u"<p>”</p>\n")

    def test_input_none(self):
        inp = None
        with self.assertRaises(TypeError):
            ast, _ = cmark.gtkdoc_to_ast(inp, self.link_resolver)
            self.assertEqual(ast, None)

    def test_resolver_none(self):
        inp = u'a'
        self.link_resolver = None
        self.assertOutputs(inp, u"<p>a</p>\n")


BASIC_GTKDOC_COMMENT = '''/**
 * test_greeter_greet:
 * @greeter: a random greeter
 *
 * This is just a function.
 */'''

SKIP_GTKDOC_COMMENT = '''/**
 * test_greeter_greet: (skip)
 */'''

LINENOS_GTKDOC_COMMENT = '''/**
 *
 *
 *
 * test_greeter_greet:
 * @greeter: a random greeter
 *
 *
 *
 *
 *
 * @not_a_param: not a parameter
 * This is just a function.
 */'''

SECTION_GTKDOC_COMMENT = '''/**
 * SECTION: notafile
 * @title: This page is not comming from a file.
 */'''

SECTION_GTKDOC_WITH_SYMBOLS = '''/**
 * SECTION: notafile
 * @title: This page is not comming from a file.
 * @auto-sort: true
 * @symbols:
 * - symbol_a
 * - symbol_b
 */'''

SECTION_WITH_NO_NEWLINE_NOR_METAS = '''/**
 * SECTION: this:
 * "this" is a section.
 */'''

NOT_A_GTKDOC_COMMENT = '''/**
 * $param rd Pointer to vbi3_raw_decoder object allocated with
 *   vbi3_raw_decoder_new().
 */'''


class TestGtkDocParser(unittest.TestCase):
    def setUp(self):
        # Cruft, should be unnecessary soon
        self.tag_validators = {}
        self.parser = GtkDocParser(self)
        self.database = Database(None)
        self.link_resolver = LinkResolver(self.database)
        self.formatter = GtkDocStringFormatter()
        Logger.silent = True
        Logger.fatal_warnings = True

    def tearDown(self):
        Logger.silent = False
        Logger.fatal_warnings = False

    def test_basic(self):
        raw = BASIC_GTKDOC_COMMENT
        lineno = 10
        end_lineno = len(raw.split('\n')) + 10 - 1
        comment = self.parser.parse_comment(
            raw,
            '/home/meh/test-greeter.c',
            lineno,
            end_lineno)

        self.assertEqual(comment.name, u'test_greeter_greet')
        self.assertEqual(len(comment.params), 1)
        self.assertTrue('greeter' in comment.params)
        param = comment.params['greeter']
        self.assertEqual(param.description, 'a random greeter')

    def test_skip_gtkdoc_comment(self):
        raw = SKIP_GTKDOC_COMMENT
        lineno = 10
        end_lineno = len(raw.split('\n')) + 10 - 1
        comment = self.parser.parse_comment(
            raw,
            None,
            lineno,
            end_lineno)
        self.assertIn('skip', comment.annotations)

    def test_not_a_gtkdoc_comment(self):
        raw = NOT_A_GTKDOC_COMMENT
        lineno = 10
        end_lineno = len(raw.split('\n')) + 10 - 1
        with self.assertRaises(HotdocSourceException):
            self.parser.parse_comment(
                raw,
                None,
                lineno,
                end_lineno)

    def test_page_name_not_a_file(self):
        raw = SECTION_GTKDOC_COMMENT
        lineno = 10
        end_lineno = len(raw.split('\n')) + 10 - 1
        comment = self.parser.parse_comment(
            raw,
            'some-file.c',
            lineno,
            end_lineno)
        self.assertEqual(comment.name, "notafile")
        self.assertEqual(comment.toplevel, True)

    def test_section_with_no_newline_nor_metas(self):
        raw_lines = SECTION_WITH_NO_NEWLINE_NOR_METAS.split("\n")

        comment = self.parser.parse_comment(
            SECTION_WITH_NO_NEWLINE_NOR_METAS,
            'some-file.c',
            0,
            len(raw_lines) - 1)

        self.assertEqual(comment.name, "this")
        self.assertEqual(comment.description, '"this" is a section.')

    def test_symbols_list(self):
        raw_lines = SECTION_GTKDOC_WITH_SYMBOLS.split("\n")

        comment = self.parser.parse_comment(
            SECTION_GTKDOC_WITH_SYMBOLS,
            'some-file.c',
            0,
            len(raw_lines) - 1)
        self.assertEqual(comment.meta['auto-sort'], True)
        self.assertEqual(comment.meta['symbols'], ['symbol_a', 'symbol_b'])

    def test_linenos(self):
        raw = LINENOS_GTKDOC_COMMENT
        lineno = 10
        end_lineno = len(raw.split('\n')) + 10 - 1
        comment = self.parser.parse_comment(
            raw,
            '/home/meh/test-greeter.c',
            lineno,
            end_lineno)
        self.assertEqual(comment.line_offset, 11)
        param = comment.params['greeter']
        self.assertEqual(param.line_offset, 5)
        self.assertEqual(param.initial_col_offset, 10)
        self.assertEqual(param.col_offset, 3)


class TestGtkDocExtension(unittest.TestCase):

    def setUp(self):
        self.database = Database(None)
        self.link_resolver = LinkResolver(self.database)
        self.link_resolver.add_link(Link("here.com", "foo", "foo"))
        self.link_resolver.add_link(Link("there.org", "there", "Test::test"))
        self.link_resolver.add_link(Link("wherever.biz", "wherever", "bar"))
        self.link_resolver.add_link(Link("whenever.net", "whenever", "Test"))
        self.link_resolver.add_link(Link("somewhere.me",
                                         "somewhere",
                                         "Test.baz"))
        self.link_resolver.add_link(Link("elsewhere.co",
                                         "elsewhere",
                                         "org.dbus.func"))

    def assertOutputs(self, inp, expected):
        ast, diagnostics = cmark.gtkdoc_to_ast(inp, self.link_resolver)
        out = cmark.ast_to_html(ast, self.link_resolver)[0]
        self.assertEqual(out, expected)
        return ast, diagnostics

    def test_existing_link(self):
        inp = u"this : #foo is a link !"
        self.assertOutputs(
            inp, '<p>this : <a href="here.com">foo</a> is a link !</p>\n')

    def test_modified_link(self):
        inp = u"this : #foo is a link !"
        ast, _ = self.assertOutputs(
            inp, '<p>this : <a href="here.com">foo</a> is a link !</p>\n')
        self.link_resolver.upsert_link(
            Link("there.com", "ze_foo", "foo"),
            overwrite_ref=True)
        out = cmark.ast_to_html(ast, self.link_resolver)[0]
        self.assertEqual(
            out,
            u'<p>this : <a href="there.com">ze_foo</a> is a link !</p>\n')

    def test_code_block(self):
        inp = u"|[\nfoo\n]|"
        self.assertOutputs(
            inp, '<pre><code>foo\n</code></pre>\n')

    def test_titled_code_block(self):
        inp = u"|[\nfoo\n]| something"
        self.assertOutputs(
            inp, '<pre><code>foo\n</code></pre>\n<p>something</p>\n')
        inp = u"|[\nfoo\n ]|something"
        self.assertOutputs(
            inp, '<pre><code>foo\n</code></pre>\n<p>something</p>\n')

    def test_syntax_boundaries(self):
        # Make sure we don't parse type links inside words
        inp = u"this : yo#foo is a link !"
        self.assertOutputs(
            inp,
            u'<p>this : yo#foo is a link !</p>\n')

        # Make sure the function link syntax doesn't take precedence
        # over classic links.
        inp = u"this is [a link]() however"
        self.assertOutputs(
            inp,
            u'<p>this is <a href="">a link</a> however</p>\n')

        # Make sure we respect code blocks
        inp = u"And `this a code block`()"
        self.assertOutputs(
            inp,
            u'<p>And <code>this a code block</code>()</p>\n')

        inp = u"And `this #too`"
        self.assertOutputs(
            inp,
            u'<p>And <code>this #too</code></p>\n')

        # Boundaries should be acceptable here
        inp = u"bar()"
        self.assertOutputs(
            inp,
            u'<p><a href="wherever.biz">wherever</a></p>\n')

        inp = u"Linking to #Test: cool"
        self.assertOutputs(
            inp,
            u'<p>Linking to <a href="whenever.net">whenever</a>: cool</p>\n')

    def test_dbus_function_link(self):
        inp = u"org.dbus.func()\n"
        self.assertOutputs(
            inp,
            u'<p><a href="elsewhere.co">elsewhere</a></p>\n')

    def test_struct_field_link(self):
        inp = u"Linking to #Test.baz yo"
        self.assertOutputs(
            inp,
            u'<p>Linking to <a href="somewhere.me">somewhere</a> yo</p>\n')

    def test_qualified_links(self):
        inp = u' #Test::test is a link'
        self.assertOutputs(
            inp,
            u'<p><a href="there.org">there</a> is a link</p>\n')

    def test_param_no_match(self):
        inp = u'Should@not@match please'
        self.assertOutputs(
            inp,
            u'<p>Should@not@match please</p>\n')

    def test_param_ref(self):
        inp = u'Should @match please'
        self.assertOutputs(
            inp,
            u'<p>Should <em>match</em> please</p>\n')

    def test_preserve_links(self):
        inp = u'Should preserve [](http://this_link.com)'
        self.assertOutputs(
            inp,
            u'<p>Should preserve <a href="http://this_link.com"></a></p>\n')

    def test_preserve_anchor_links(self):
        inp = u'Should preserve [](#this-anchor-link)'
        self.assertOutputs(
            inp,
            u'<p>Should preserve <a href="#this-anchor-link"></a></p>\n')

    def test_wrong_link(self):
        inp = u'this #does_not_exist'
        _, diagnostics = self.assertOutputs(
            inp,
            u'<p>this does_not_exist</p>\n')
        self.assertEqual(len(diagnostics), 1)
        diag = diagnostics[0]
        self.assertEqual(
            diag.message,
            (u'Trying to link to non-existing symbol ‘does_not_exist’'))
        self.assertEqual(diag.lineno, 0)
        self.assertEqual(diag.column, 5)

    def test_link_parsing_context(self):
        inp = u'A %NULL-terminated thing'
        _, diagnostics = self.assertOutputs(
            inp,
            u'<p>A NULL-terminated thing</p>\n')
        self.assertEqual(len(diagnostics), 1)
        diag = diagnostics[0]
        self.assertEqual(
            diag.message,
            (u'Trying to link to non-existing symbol ‘NULL’'))
        inp = u'A #Object::dashed-signal'
        _, diagnostics = self.assertOutputs(
            inp,
            u'<p>A Object::dashed-signal</p>\n')
        self.assertEqual(len(diagnostics), 1)
        diag = diagnostics[0]
        self.assertEqual(
            diag.message,
            (u'Trying to link to non-existing symbol ‘Object::dashed-signal’'))

    def test_wrong_function_link(self):
        inp = u'does_not_exist()'
        _, diagnostics = self.assertOutputs(
            inp,
            u'<p>does_not_exist</p>\n')

        self.assertEqual(len(diagnostics), 1)
        diag = diagnostics[0]
        self.assertEqual(
            diag.message,
            (u'Trying to link to non-existing symbol ‘does_not_exist’'))
        self.assertEqual(diag.lineno, 0)
        self.assertEqual(diag.column, 0)

    def test_wrong_multiline_link(self):
        inp = (u'a #wrong_link\n\n'
               'and #another_wrong_link\n'
               'and then #yet_another_wrong_link')
        _, diagnostics = cmark.gtkdoc_to_ast(inp, self.link_resolver)
        self.assertEqual(len(diagnostics), 3)
        diag = diagnostics[0]
        self.assertEqual(diag.lineno, 0)
        self.assertEqual(diag.column, 2)
        diag = diagnostics[1]
        self.assertEqual(diag.lineno, 2)
        self.assertEqual(diag.column, 4)
        diag = diagnostics[2]
        self.assertEqual(diag.lineno, 3)
        self.assertEqual(diag.column, 9)


class MockIncludeResolver:

    def resolve(self, filename):
        if filename == 'simple_file.md':
            return "simple file"
        if filename == 'empty_file.markdown':
            return ""
        if filename == 'opens_code_block.md':
            return "```"
        if filename == 'unicode_file.md':
            return u"some Ünicode"
        return None


class TestIncludeExtension(unittest.TestCase):

    def setUp(self):
        self.database = Database(None)
        self.link_resolver = LinkResolver(self.database)
        self.include_resolver = MockIncludeResolver()

    def assertOutputs(self, inp, expected):
        ast = cmark.hotdoc_to_ast(inp, self.include_resolver)
        out = cmark.ast_to_html(ast, self.link_resolver)[0]
        self.assertEqual(out, expected)
        return out, ast

    def test_basic(self):
        inp = u'   I include a {{simple_file.md}}!'
        self.assertOutputs(inp,
                           u'<p>I include a simple file!</p>\n')

    def test_no_such_file(self):
        inp = u'I include a {{should_not_exist}}!'
        self.assertOutputs(
            inp,
            u'<p>I include a {{should_not_exist}}!</p>\n')

    def test_in_code_block(self):
        inp = (u'```\n'
               '{{simple_file.md}}\n'
               '```\n')
        self.assertOutputs(
            inp,
            u'<pre><code>{{simple_file.md}}\n'
            '</code></pre>\n')

    def test_multiple_includes(self):
        inp = (u'I include a {{simple_file.md}} and '
               'another {{simple_file.md}}!\n')
        self.assertOutputs(inp,
                           u'<p>I include a simple file and '
                           'another simple file!</p>\n')

    def test_include_opens_code_block(self):
        inp = (u'I include\n'
               '{{opens_code_block.md}}{{simple_file.md}}')

        self.assertOutputs(
            inp,
            (u'<p>I include</p>\n'
             '<pre><code class="language-{{simple_file.md}}">'
             '</code></pre>\n'))

    def test_empty_file(self):
        inp = u'I include an empty file{{empty_file.markdown}}!'
        self.assertOutputs(
            inp,
            u'<p>I include an empty file!</p>\n')

    def test_unicode(self):
        inp = u'I include a file containing Unicode {{unicode_file.md}}!'
        self.assertOutputs(
            inp,
            u'<p>I include a file containing Unicode some Ünicode!</p>\n')


class TestTableExtension(unittest.TestCase):
    def setUp(self):
        self.database = Database(None)
        self.link_resolver = LinkResolver(self.database)
        self.include_resolver = MockIncludeResolver()

    def render(self, inp):
        ast = cmark.hotdoc_to_ast(inp, self.include_resolver)
        out = cmark.ast_to_html(ast, self.link_resolver)[0]
        return ast, out

    def assertOutputs(self, inp, expected):
        ast, out = self.render(inp)
        self.assertEqual(out, expected)
        return ast

    def test_table_with_header(self):
        inp = u'\n'.join(['| h1 | h2 |',
                          '| -- | -- |',
                          '| c1 | c2 |'])
        expected = u'\n'.join(['<table>',
                               '<thead>',
                               '<tr>',
                               '<th> h1</th>',
                               '<th> h2</th>',
                               '</tr>',
                               '</thead>',
                               '<tbody>',
                               '<tr>',
                               '<td> c1</td>',
                               '<td> c2</td>',
                               '</tr></tbody></table>'])
        self.assertOutputs(inp, expected)

    def test_invalid_table_no_marker_row(self):
        inp = u'\n'.join(['| h1 | h2 |',
                          'Hello you ..\n'])
        expected = '\n'.join(['<p>| h1 | h2 |',
                              'Hello you ..</p>',
                              ''])
        self.assertOutputs(inp, expected)

    def test_table_no_header(self):
        inp = u'\n'.join(['| -- | -- |',
                          '| c1 | c2 |'])
        expected = '\n'.join(['<table>',
                              '<tr>',
                              '<td> c1</td>',
                              '<td> c2</td>',
                              '</tr></table>'])
        self.assertOutputs(inp, expected)

    def test_html_in_table(self):
        inp = u'\n'.join(['| <b>bold</bold> | normal |',
                          '| - | - |',
                          '| <i>italic</i> | normal |'])

        expected = u'\n'.join(['<table>',
                               '<thead>',
                               '<tr>',
                               '<th> <b>bold</bold></th>',
                               '<th> normal</th>',
                               '</tr>',
                               '</thead>',
                               '<tbody>',
                               '<tr>',
                               '<td> <i>italic</i></td>',
                               '<td> normal</td>',
                               '</tr></tbody></table>'])
        self.assertOutputs(inp, expected)


class TestAutoRefExtension(unittest.TestCase):
    def render(self, inp):
        ast = cmark.hotdoc_to_ast(inp, None)
        out = cmark.ast_to_html(ast, None)[0]
        return ast, out

    def assertOutputs(self, inp, expected):
        ast, out = self.render(inp)
        self.assertEqual(out, expected)
        return ast

    def test_basic(self):
        inp = (u'doing an [auto ref] yo\n'
               '\n'
               '# Auto ref\n')
        exp = (u'<p>doing an <a href="#auto-ref">auto ref</a> yo</p>\n'
               '<h1>Auto ref</h1>\n')
        self.assertOutputs(inp, exp)

    def test_unicode(self):
        inp = (u'doing a [Ünicode] auto ref yo\n'
               u'\n'
               u'# Ünicode\n')
        exp = (u'<p>doing a <a href="#nicode">Ünicode</a> auto ref yo</p>\n'
               u'<h1>Ünicode</h1>\n')
        self.assertOutputs(inp, exp)
