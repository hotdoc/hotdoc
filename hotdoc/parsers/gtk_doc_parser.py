#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module implements a parsing utilities for the legacy
gtk-doc comment format.
"""

import cgi
import re
import sys
from itertools import izip_longest
from xml.sax.saxutils import unescape

import cmarkpy

from hotdoc.core.comment_block import Comment, Annotation, Tag
from hotdoc.core.file_includer import add_md_includes
from hotdoc.utils.configurable import Configurable


# http://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
def _grouper(iterable, n_args, fillvalue=None):
    """
    Banana banana
    """
    args = [iter(iterable)] * n_args
    return izip_longest(*args, fillvalue=fillvalue)


# pylint: disable=too-few-public-methods
class GtkDocParser(object):
    """
    Banana banana
    """

    def __init__(self, doc_repo):
        """
        Lifted from
        http://stackoverflow.com/questions/5323703/regex-how-to-match-sequence-of-key-value-pairs-at-end-of-string
        """
        self.kv_regex = re.compile(r'''
                                   [\S]+=
                                   (?:
                                   \s*
                                   (?!\S+=)\S+
                                   )+
                                   ''', re.VERBOSE)
        self.doc_repo = doc_repo

        tag_validation_regex = r'((?:^|\n)[ \t]*('
        tag_validation_regex += 'returns|Returns|since|Since|deprecated'\
            '|Deprecated|stability|Stability|Return value'
        for validator in doc_repo.tag_validators.values():
            tag_validation_regex += '|%s|%s' % (validator.name,
                                                validator.name.lower())
        tag_validation_regex += '):)'

        self.tag_validation_regex = re.compile(tag_validation_regex)

    def __parse_title(self, raw_title):
        # Section comments never contain annotations,
        # We also normalize them here to not contain any spaces.
        # FIXME: This code now only lives here for the purpose of
        # gtk-doc conversion
        # Could remove that one day
        if "SECTION" in raw_title:
            return ''.join(raw_title.split(' ')), []

        split = raw_title.split(': ', 1)
        title = split[0].rstrip(':')
        annotations = []
        if len(split) > 1:
            annotations = self.__parse_annotations(split[1])
        elif not raw_title.strip().endswith(':'):
            print "Missing colon in comment name :", raw_title
            return None, []
        return title, annotations

    def __parse_key_value_annotation(self, name, string):
        kvs = self.kv_regex.findall(string)
        kvs = dict([kv.split('=', 1) for kv in kvs])
        return Annotation(name=name, argument=kvs)

    def __parse_annotation(self, string):
        split = string.split()
        name = split[0].strip()
        if len(split) == 1:
            return Annotation(name=name)
        elif '=' in split[1]:
            return self.__parse_key_value_annotation(name, split[1])
        else:
            return Annotation(name=name, argument=[split[1]])

    def __parse_annotations(self, string):
        parsed_annotations = []
        par_level = 0
        current_annotation = ""
        for _ in string:
            if _ == '(':
                par_level += 1
            elif _ == ')':
                par_level -= 1

            if par_level > 1:
                return []
            elif par_level == 1 and _ not in '()':
                current_annotation += _
            elif par_level == 0:
                if _ not in ' \t\n\r()':
                    return []
                if current_annotation:
                    ann = self.__parse_annotation(current_annotation)
                    if ann:
                        parsed_annotations.append(ann)
                    current_annotation = ""
            elif par_level < 0:
                return []

        if par_level != 0:
            return []

        return parsed_annotations

    def __extract_annotations(self, desc):
        split = desc.split(': ', 1)

        if len(split) == 1:
            return desc, []

        annotations = self.__parse_annotations(split[0])
        if not annotations:
            return desc, []

        return split[1].strip(), annotations

    def __parse_parameter(self, name, desc):
        name = name.strip()[1:-1].strip()
        desc = desc.strip()
        desc, annotations = self.__extract_annotations(desc)
        annotations = {annotation.name: annotation for annotation in
                       annotations}
        return Comment(name=name, annotations=annotations,
                       description=desc)

    def __parse_title_and_parameters(self, title_and_params):
        tps = re.split(r'(\n[ \t]*@[\S]+[ \t]*:)', title_and_params)
        title, annotations = self.__parse_title(tps[0])
        parameters = []
        for name, desc in _grouper(tps[1:], 2):
            parameters.append(self.__parse_parameter(name, desc))
        return title, parameters, annotations

    # pylint: disable=no-self-use
    def __parse_since_tag(self, name, desc):
        return Tag(name=name, description=desc)

    # pylint: disable=no-self-use
    def __parse_deprecated_tag(self, name, desc):
        return Tag(name=name, description=desc)

    # pylint: disable=no-self-use
    def __parse_stability_tag(self, name, desc):
        return Tag(name=name, description=desc)

    # pylint: disable=no-self-use
    def __parse_returns_tag(self, name, desc):
        desc, annotations = self.__extract_annotations(desc)
        annotations = {annotation.name: annotation for annotation in
                       annotations}
        return Tag(name=name, annotations=annotations, description=desc)

    # pylint: disable=too-many-return-statements
    def __parse_tag(self, name, desc):
        if name.lower() == "since":
            return self.__parse_since_tag(name, desc)
        elif name.lower() == "returns":
            return self.__parse_returns_tag(name, desc)
        elif name.lower() == "return value":
            return self.__parse_returns_tag("returns", desc)
        elif name.lower() == "stability":
            return self.__parse_stability_tag("stability", desc)
        elif name.lower() == "deprecated":
            return self.__parse_deprecated_tag("deprecated", desc)
        else:
            validator = self.doc_repo.tag_validators.get(name)
            if not validator:
                print "FIXME no tag validator"
                return None
            if not validator.validate(desc):
                print "invalid value for tag %s : %s" % name, desc
                return None
            return Tag(name=name, description=desc)

    def __parse_description_and_tags(self, desc_and_tags):
        dts = self.tag_validation_regex.split(desc_and_tags)
        tags = []

        desc = dts[0]
        if len(dts) == 1:
            return desc, tags

        # pylint: disable=unused-variable
        for raw, name, tag_desc in _grouper(dts[1:], 3):
            tag = self.__parse_tag(name.strip(), tag_desc.strip())
            if tag:
                tags.append(tag)

        return desc, tags

    def __strip_comment(self, comment):
        comment = re.sub(r'^[\W]*\/[\*]+[\W]*', '', comment)
        comment = re.sub(r'\*\/[\W]*$', '', comment)
        comment = re.sub(r'\n[ \t]*\*', '\n', comment)
        return comment.strip()

    def __validate_c_comment(self, comment):
        return re.match(r'(/\*\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)$',
                        comment) is not None

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    def parse_comment(self, comment, filename, lineno, endlineno,
                      include_paths=None, stripped=False):
        """
        Returns a Comment given a string
        """
        if not stripped and not self.__validate_c_comment(comment.strip()):
            return None

        raw_comment = comment
        if not stripped:
            comment = self.__strip_comment(comment)

        comment = add_md_includes(unicode(comment.decode('utf8')),
                                  filename, include_paths, lineno)

        split = re.split(r'\n[\W]*\n', comment, maxsplit=1)
        block_name, parameters, annotations = \
            self.__parse_title_and_parameters(split[0])

        if not block_name:
            return None

        description = ""
        tags = []
        if len(split) > 1:
            description, tags = self.__parse_description_and_tags(split[1])

        title = None
        short_description = None
        actual_parameters = {}
        for param in parameters:
            if param.name.lower() == 'short_description':
                short_description = param.description
            elif param.name.lower() == 'title':
                title = param.description
            else:
                actual_parameters[param.name] = param

        annotations = {annotation.name: annotation for annotation in
                       annotations}
        tags = {tag.name.lower(): tag for tag in tags}

        block = Comment(name=block_name, filename=filename, lineno=lineno,
                        endlineno=endlineno,
                        annotations=annotations, params=actual_parameters,
                        description=description,
                        short_description=short_description,
                        title=title, tags=tags, raw_comment=raw_comment)

        return block


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


class GtkDocStringFormatter(Configurable):
    """
    A parser for the legacy gtk-doc format.
    """

    remove_xml_tags = False

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

        if GtkDocStringFormatter.remove_xml_tags:
            text = re.sub('<.*?>', '', text)

        text = unescape(text)

        out = self.__legacy_to_md(text, link_resolver)

        if output_format == 'markdown':
            return out
        elif output_format == 'html':
            return self.__md_to_html(out)

        raise Exception("Unrecognized format %s" % output_format)

    @staticmethod
    def add_arguments(parser):
        """Banana banana
        """
        group = parser.add_argument_group(
            'GtkDocStringFormatter', 'GtkDocStringFormatter options')
        group.add_argument("--gtk-doc-remove-xml", action="store_true",
                           dest="gtk_doc_remove_xml", help="Remove xml?")

    @staticmethod
    def parse_config(doc_repo, config):
        """Banana banana
        """
        GtkDocStringFormatter.remove_xml_tags = config.get(
            'gtk_doc_remove_xml')

if __name__ == "__main__":
    PARSER = GtkDocStringFormatter()
    with open(sys.argv[1], 'r') as f:
        CONTENTS = f.read()
        print PARSER.translate(CONTENTS, None, 'html')
