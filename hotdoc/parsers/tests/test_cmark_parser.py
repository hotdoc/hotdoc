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

import unittest
from hotdoc.parsers import cmark
from hotdoc.core.doc_database import DocDatabase
from hotdoc.core.links import LinkResolver, Link


class TestParser(unittest.TestCase):

    def setUp(self):
        self.doc_database = DocDatabase()
        self.link_resolver = LinkResolver(self.doc_database)
        self.link_resolver.add_link(Link("here.com", "foo", "foo"))

    def assertOutputs(self, inp, expected):
        ast = cmark.gtkdoc_to_ast(inp, self.link_resolver)
        out = cmark.ast_to_html(ast, self.link_resolver)
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
            ast = cmark.gtkdoc_to_ast(inp, self.link_resolver)
            self.assertEqual(ast, None)

    def test_resolver_none(self):
        inp = u'a'
        self.link_resolver = None
        self.assertOutputs(inp, u"<p>a</p>\n")


class TestGtkDocExtension(unittest.TestCase):

    def setUp(self):
        self.doc_database = DocDatabase()
        self.link_resolver = LinkResolver(self.doc_database)
        self.link_resolver.add_link(Link("here.com", "foo", "foo"))
        self.link_resolver.add_link(Link("there.org", "there", "Test::test"))

    def assertOutputs(self, inp, expected):
        ast = cmark.gtkdoc_to_ast(inp, self.link_resolver)
        out = cmark.ast_to_html(ast, self.link_resolver)
        self.assertEqual(out, expected)
        return ast

    def test_existing_link(self):
        inp = u"this : #foo is a link !"
        self.assertOutputs(
            inp, '<p>this : <a href="here.com">foo</a> is a link !</p>\n')

    def test_modified_link(self):
        inp = u"this : #foo is a link !"
        ast = self.assertOutputs(
            inp, '<p>this : <a href="here.com">foo</a> is a link !</p>\n')
        self.link_resolver.upsert_link(
            Link("there.com", "ze_foo", "foo"),
            overwrite_ref=True)
        out = cmark.ast_to_html(ast, self.link_resolver)
        self.assertEqual(
            out,
            u'<p>this : <a href="there.com">ze_foo</a> is a link !</p>\n')

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
        inp = u"function_link()"
        self.assertOutputs(
            inp,
            u'<p><a href="function_link">function_link</a></p>\n')

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


class MockIncludeResolver(object):

    def resolve(self, filename):
        if filename == 'simple_file.md':
            return "simple file"
        elif filename == 'empty_file.markdown':
            return ""
        elif filename == 'opens_code_block.md':
            return "```"
        return None


class TestIncludeExtension(unittest.TestCase):

    def setUp(self):
        self.doc_database = DocDatabase()
        self.link_resolver = LinkResolver(self.doc_database)
        self.include_resolver = MockIncludeResolver()

    def assertOutputs(self, inp, expected):
        ast = cmark.hotdoc_to_ast(inp, self.include_resolver)
        out = cmark.ast_to_html(ast, self.link_resolver)
        self.assertEqual(out, expected)
        return ast

    def test_basic(self):
        inp = u'I include a {{simple_file.md}}!'
        self.assertOutputs(inp,
                           u'<p>I include a simple file!</p>\n')

    def test_no_such_file(self):
        inp = u'I include a {{should_not_exist}}!'
        self.assertOutputs(
            inp,
            u'<p>I include a FIXME: missing include: should_not_exist!</p>\n')

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
