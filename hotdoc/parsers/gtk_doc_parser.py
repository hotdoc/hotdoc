#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module implements a parsing utilities for the legacy
gtk-doc comment format.
"""

import cgi
import re
import sys
from xml.sax.saxutils import unescape

import cmarkpy


def _unmangle_specs(specs):
    mangled = re.compile('<<([a-zA-Z_:]+)>>')
    specdict = dict((name.lstrip('!'), spec) for name, spec in specs)

    def _unmangle(spec, name=None):
        def _replace_func(match):
            child_spec_name = match.group(1)

            if ':' in child_spec_name:
                pattern_name, child_spec_name = child_spec_name.split(
                    ':', 1)
            else:
                pattern_name = None

            child_spec = specdict[child_spec_name]
            # Force all child specs of this one to be unnamed
            unmangled = _unmangle(child_spec, None)
            if pattern_name and name:
                return '(?P<%s_%s>%s)' % (name, pattern_name, unmangled)
            else:
                return unmangled

        return mangled.sub(_replace_func, spec)

    return [(name, _unmangle(spec, name)) for name, spec in specs]


def _make_regex(specs):
    regex = '|'.join('(?P<%s>%s)' % (name, spec) for name, spec in specs
                     if not name.startswith('!'))
    return re.compile(regex)


def _get_properties(name, match):
    groupdict = match.groupdict()
    properties = {name: groupdict.pop(name)}
    name = name + "_"
    for group, value in groupdict.iteritems():
        if group.startswith(name):
            key = group[len(name):]
            properties[key] = value
    return properties

# Lifted from g-ir-doc-tool, muahaha
# pylint: disable=too-few-public-methods


class DocScanner(object):
    """
    Banana banana
    """

    def __init__(self):
        specs = [
            ('!alpha', r'[a-zA-Z0-9_]+'),
            ('!alpha_dash', r'[a-zA-Z0-9_-]+'),
            ('!anything', r'.*'),
            ('note', r'\n+>\s*<<note_contents:anything>>\s*\n'),
            ('new_paragraph', r'\n\n'),
            ('new_line', r'\n'),
            ('code_start_with_language',
             r'\|\[\<!\-\-\s*language\s*\=\s*\"<<language_name:alpha>>\"'
             r'\s*\-\-\>'),
            ('code_start', r'\|\['),
            ('code_end', r'\]\|'),
            ('property',
             r'#<<type_name:alpha>>:(<<property_name:alpha_dash>>)'),
            ('signal', r'#<<type_name:alpha>>::(<<signal_name:alpha_dash>>)'),
            ('type_name', r'#(<<type_name:alpha>>)'),
            ('enum_value', r'%(<<member_name:alpha>>)'),
            ('parameter', r'@<<param_name:alpha>>'),
            ('function_call', r'<<symbol_name:alpha>>\s*\(\)'),
            ('include', r'{{\s*<<include_name:anything>>\s*}}'),
        ]
        self.specs = _unmangle_specs(specs)
        self.regex = _make_regex(self.specs)

    def scan(self, text):
        """
        Generates tuples made of:
        (token type name, token, token properties)
        """
        pos = 0
        while True:
            match = self.regex.search(text, pos)
            if match is None:
                break

            start = match.start()
            if start > pos:
                yield ('other', text[pos:start], None)

            pos = match.end()
            name = match.lastgroup
            yield (name, match.group(0), _get_properties(name, match))

        if pos < len(text):
            yield ('other', text[pos:], None)


class GtkDocStringFormatter(object):
    """
    A parser for the legacy gtk-doc format.
    """

    def __init__(self):
        self.funcs = {
            'other': self.__format_other,
            'new_line': self.__format_other,
            'new_paragraph': self.__format_other,
            'note': self.__format_other,
            'include': self.__format_other,
            'property': self.__format_property,
            'signal': self.__format_signal,
            'type_name': self.__format_type_name,
            'enum_value': self.__format_enum_value,
            'parameter': self.__format_parameter,
            'function_call': self.__format_function_call,
            'code_start': self.__format_code_start,
            'code_start_with_language': self.__format_code_start_with_language,
            'code_end': self.__format_code_end,
        }

        self.__doc_scanner = DocScanner()

    # pylint: disable=unused-argument
    # pylint: disable=no-self-use
    def __format_other(self, match, props, link_resolver):
        return match

    def __format_property(self, match, props, link_resolver):
        type_name = props['type_name']
        property_name = props['property_name']

        if link_resolver is None:
            return u'[](%s:%s)' % (type_name, property_name)

        linkname = "%s:%s" % (type_name, property_name)
        link = link_resolver.get_named_link(linkname)

        if link:
            return u"[“%s”](%s)" % (link.title, link.get_link())
        else:
            return u"the %s's “%s” property" % (type_name, property_name)

    def __format_signal(self, match, props, link_resolver):
        type_name = props['type_name']
        signal_name = props['signal_name']
        if link_resolver is None:
            return u'[](%s::%s)' % (type_name, signal_name)

        linkname = "%s::%s" % (type_name, signal_name)
        link = link_resolver.get_named_link(linkname)

        if link:
            return u"[“%s”](%s)" % (link.title, link.get_link())
        else:
            return u"the %s's “%s” signal" % (type_name, signal_name)

    def __format_type_name(self, match, props, link_resolver):
        type_name = props['type_name']

        # It is assumed that when there is a name collision
        # between a struct and a class name, the link is to be made
        # to the class

        if link_resolver is None:
            return u'[](%s)' % (type_name)

        class_name = '%s::%s' % (type_name, type_name)
        link = link_resolver.get_named_link(class_name)

        if link is None:
            link = link_resolver.get_named_link(type_name)

        if link:
            return "[%s](%s)" % (link.title, link.get_link())
        else:
            return match

    def __format_enum_value(self, match, props, link_resolver):
        member_name = props['member_name']

        if link_resolver is None:
            return '[](%s)' % member_name

        link = link_resolver.get_named_link(member_name)

        if link:
            return "[%s](%s)" % (link.title, link.get_link())
        else:
            return match

    def __format_parameter(self, match, props, link_resolver):
        param_name = props['param_name']
        return '_%s_' % param_name

    def __format_function_call(self, match, props, link_resolver):
        func_name = props['symbol_name']
        if link_resolver is None:
            return '[](%s)' % func_name

        link = link_resolver.get_named_link(func_name)

        if link:
            return "[%s()](%s)" % (link.title, link.get_link())
        else:
            return match

    def __format_code_start(self, match, props, link_resolver):
        return "\n```\n"

    # pylint: disable=invalid-name
    def __format_code_start_with_language(self, match, props, link_resolver):
        return "\n```%s\n" % props["language_name"]

    def __format_code_end(self, match, props, link_resolver):
        return "\n```\n"

    def __md_to_html(self, md):
        out = cgi.escape(md)
        rendered_text = cmarkpy.markdown_to_html(unicode(out))
        return rendered_text

    def __legacy_to_md(self, text, link_resolver):
        out = u''

        tokens = self.__doc_scanner.scan(text)
        in_code = False
        for tok in tokens:
            kind, match, props = tok
            formatted = self.funcs[kind](match, props, link_resolver)
            if kind == "code_end":
                in_code = False
            if in_code:
                out += match
            else:
                out += formatted
            if kind in ["code_start", "code_start_with_language"]:
                in_code = True

        return out

    def translate(self, text, link_resolver, output_format):
        """
        Given a gtk-doc comment string, returns the comment translated
        to the desired format.
        """
        out = u''

        if not text:
            return out

        text = unescape(text)

        out = self.__legacy_to_md(text, link_resolver)

        if output_format == 'markdown':
            return out
        elif output_format == 'html':
            return self.__md_to_html(out)

        raise Exception("Unrecognized format %s" % output_format)

if __name__ == "__main__":
    PARSER = GtkDocStringFormatter()
    with open(sys.argv[1], 'r') as f:
        CONTENTS = f.read()
        print PARSER.translate(CONTENTS, None, 'html')
