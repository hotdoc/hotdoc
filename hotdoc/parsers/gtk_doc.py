#!/usr/bin/env python
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

"""
This module implements parsing utilities for the legacy
gtk-doc comment format.
"""

import os
import re
import cgi
from collections import OrderedDict
from itertools import zip_longest
from xdg import XDG_DATA_HOME, XDG_DATA_DIRS
from lxml import etree

import yaml
from yaml.constructor import ConstructorError

from hotdoc.core.comment import (Comment, Annotation, Tag,
                                 comment_from_tag)
from hotdoc.core.exceptions import HotdocSourceException
from hotdoc.core.links import Link
from hotdoc.utils.configurable import Configurable
from hotdoc.parsers import cmark
from hotdoc.utils.loggable import Logger, warn, info

Logger.register_warning_code('gtk-doc', HotdocSourceException)
Logger.register_warning_code('gtk-doc-bad-link', HotdocSourceException)
Logger.register_warning_code('gtk-doc-bad-syntax', HotdocSourceException)


GTKDOC_HREFS = {}


GATHERED_GTKDOC_LINKS = False


# http://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
def _grouper(iterable, n_args, fillvalue=None):
    """
    Banana banana
    """
    args = [iter(iterable)] * n_args
    return zip_longest(*args, fillvalue=fillvalue)


# pylint: disable=too-few-public-methods
class GtkDocParser:
    """
    Banana banana
    """

    def __init__(self, project, section_file_matching=True):
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
        self.project = project

        tag_validation_regex = r'((?:^|\n)[ \t]*('
        tag_validation_regex += 'returns|Returns|since|Since|deprecated'\
            '|Deprecated|stability|Stability|Return value|topic|Topic'
        for validator in list(project.tag_validators.values()):
            tag_validation_regex += '|%s|%s' % (validator.name,
                                                validator.name.lower())
        tag_validation_regex += '):)'

        self.tag_validation_regex = re.compile(tag_validation_regex)
        self.__section_file_matching = section_file_matching

    def __parse_title(self, source_filename, raw_title):
        if raw_title.startswith('SECTION'):
            section_name = raw_title.split('SECTION:')[1].strip()
            return section_name, [], True

        split = raw_title.split(': ', 1)

        title = split[0].rstrip(':')
        if not len(split) > 1 and not title.endswith(':') and " " in title:
            raise HotdocSourceException(
                message='Unexpected title in gtk-doc comment')

        annotations = []

        if len(split) > 1:
            annotations = self.__parse_annotations(split[1])
        return title, annotations, False

    def __parse_key_value_annotation(self, name, string):
        kvs = self.kv_regex.findall(string)
        kvs = {kv.split('=', 1)[0]: kv.split('=', 1)[1] for kv in kvs}
        return Annotation(name=name, argument=kvs)

    def __parse_annotation(self, string):
        split = string.split()
        name = split[0].strip()
        if len(split) == 1:
            return Annotation(name=name)
        if '=' in split[1]:
            return self.__parse_key_value_annotation(name, split[1])
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
            if par_level == 1 and _ not in '()':
                current_annotation += _
            elif par_level == 0:
                if _ not in ' \t\n\r():':
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
        raw_comment = '%s:%s' % (name, desc)
        desc = desc.strip()
        desc, annotations = self.__extract_annotations(desc)
        annotations = {annotation.name: annotation for annotation in
                       annotations}
        return Comment(name=name, annotations=annotations,
                       meta={'description': desc}, raw_comment=raw_comment)

    def __parse_title_and_parameters(self, filename, title_and_params):
        tps = re.split(r'(\n[ \t]*@[\S]+[ \t]*:)', title_and_params)
        title, annotations, is_section = self.__parse_title(filename, tps[0])
        parameters = []
        for name, desc in _grouper(tps[1:], 2):
            n_chars = len(name.strip()) + len(desc)
            param = self.__parse_parameter(name, desc)
            param.line_offset = len(desc.split('\n'))
            parameters.append(param)
            param.initial_col_offset = n_chars - len(param.description)
        return title, parameters, annotations, is_section

    # pylint: disable=no-self-use
    def __parse_since_tag(self, name, desc):
        return Tag(name, desc, value=desc)

    def __parse_topic_tag(self, name, desc):
        return Tag(name, None, value=desc)

    # pylint: disable=no-self-use
    def __parse_deprecated_tag(self, name, desc):
        split = desc.split(':', 1)
        if len(split) == 2 and len(split[0]) > 1:
            value = split[0]
            if ' ' in value:
                value = None
        else:
            value = None

        return Tag(name, desc, value=value)

    # pylint: disable=no-self-use
    def __parse_stability_tag(self, name, desc):
        value = desc.strip().lower()
        if value not in ('private', 'stable', 'unstable'):
            # FIXME warn
            return None
        return Tag(name, desc, value=value)

    # pylint: disable=no-self-use
    def __parse_returns_tag(self, name, desc):
        desc, annotations = self.__extract_annotations(desc)
        annotations = {annotation.name: annotation for annotation in
                       annotations}
        return Tag(name, desc, annotations=annotations)

    # pylint: disable=too-many-return-statements
    def __parse_tag(self, name, desc):
        if name.lower() == "since":
            return self.__parse_since_tag(name, desc)
        if name.lower() == "returns":
            return self.__parse_returns_tag(name, desc)
        if name.lower() == "return value":
            return self.__parse_returns_tag("returns", desc)
        if name.lower() == "stability":
            return self.__parse_stability_tag("stability", desc)
        if name.lower() == "deprecated":
            return self.__parse_deprecated_tag("deprecated", desc)
        if name.lower() == "topic":
            return self.__parse_topic_tag("topic", desc)

        validator = self.project.tag_validators.get(name)
        if not validator:
            warn('gtk-doc', "FIXME no tag validator")
            return None
        if not validator.validate(desc):
            warn('gtk-doc', "invalid value for tag %s : %s" % (name, desc))
            return None
        return Tag(name=name, description=desc, value=desc)

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
            else:
                desc += '\n%s: %s' % (name, tag_desc)

        return desc, tags

    def __strip_comment(self, comment):
        n_lines = len(comment.split('\n'))
        comment = re.sub(r'^[\W]*\/[\*]+[\W]*', '', comment)
        title_offset = n_lines - len(comment.split('\n'))
        comment = re.sub(r'\*\/[\W]*$', '', comment)
        comment = re.sub(r'\n[ \t]*\*', '\n', comment)
        return comment.strip(), title_offset

    def __validate_c_comment(self, comment):
        return re.match(r'(/\*\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)$',
                        comment) is not None

    def __parse_yaml_comment(self, comment, filename):
        res = {}
        try:
            blocks = yaml.load_all(comment.raw_comment, Loader=yaml.SafeLoader)
            for block in blocks:
                if block:
                    res.update(block)
        except (ConstructorError, yaml.parser.ParserError) as exception:
            warn('invalid-page-metadata',
                 '%s: Invalid metadata: \n%s' % (filename, str(exception)))
        return res

    def __extract_titles_params_and_description(self, comment):
        titleandparams_description = re.split(r'\n[\s]*\n', comment, maxsplit=1)
        title_and_params = titleandparams_description[0]

        title_and_params_lines = title_and_params.split('\n')
        if len(title_and_params_lines) > 1 and not title_and_params_lines[1].strip().startswith('@'):
            return title_and_params_lines[0].rstrip(':'), '\n'.join([l.strip() for l in title_and_params_lines[1:]])

        if len(titleandparams_description) > 1:
            description = titleandparams_description[1]
        else:
            description = None

        return title_and_params, description

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=unused-argument
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def parse_comment(self, comment, filename, lineno, endlineno,
                      include_paths=None, stripped=False):
        """
        Returns a Comment given a string
        """
        if not stripped and not self.__validate_c_comment(comment.strip()):
            return None

        title_offset = 0

        column_offset = 0

        raw_comment = comment
        if not stripped:
            try:
                while comment[column_offset * -1 - 1] != '\n':
                    column_offset += 1
            except IndexError:
                column_offset = 0
            comment, title_offset = self.__strip_comment(comment)

        title_and_params, description = self.__extract_titles_params_and_description(comment)
        try:
            block_name, parameters, annotations, is_section = \
                self.__parse_title_and_parameters(filename, title_and_params)
        except HotdocSourceException as _:
            warn('gtk-doc-bad-syntax',
                 message=_.message,
                 filename=filename,
                 lineno=lineno + title_offset)
            return None

        params_offset = 0
        for param in parameters:
            param.filename = filename
            param.lineno = lineno
            param_offset = param.line_offset
            param.line_offset = title_offset + params_offset + 1
            params_offset += param_offset
            param.col_offset = column_offset

        if not block_name:
            return None

        description_offset = 0
        meta = {}
        tags = []
        if description is not None:
            n_lines = len(comment.split('\n'))
            description_offset = (title_offset + n_lines -
                                  len(description.split('\n')))
            meta['description'], tags = self.__parse_description_and_tags(description)

        actual_parameters = OrderedDict({})
        for param in parameters:
            if is_section:
                cleaned_up_name = param.name.lower().replace('_', '-')
                if cleaned_up_name in ['symbols', 'private-symbols', 'auto-sort', 'sources']:
                    meta.update(self.__parse_yaml_comment(param, filename))
                    if cleaned_up_name == 'sources':
                        sources_paths = [os.path.abspath(os.path.join(os.path.dirname(filename), path)) for path in meta[cleaned_up_name]]
                        meta[cleaned_up_name] = sources_paths
                else:
                    meta[param.name] = param.description
            else:
                actual_parameters[param.name] = param

        annotations = {annotation.name: annotation for annotation in
                       annotations}
        tags = {tag.name.lower(): tag for tag in tags}

        block = Comment(name=block_name, filename=filename, lineno=lineno,
                        endlineno=endlineno,
                        annotations=annotations, params=actual_parameters,
                        tags=tags, raw_comment=raw_comment,
                        meta=meta, toplevel=is_section)
        block.line_offset = description_offset
        block.col_offset = column_offset

        return block


class GtkDocStringFormatter(Configurable):
    """
    A parser for the legacy gtk-doc format.
    """

    def __init__(self):
        self.remove_xml_tags = False
        self.escape_html = False
        self.gdbus_codegen_sources = []

    # pylint: disable=no-self-use
    def comment_to_ast(self, comment, link_resolver, include_resolver):
        """
        Given a gtk-doc comment string, returns an opaque PyCapsule
        containing the document root.

        This is an optimization allowing to parse the docstring only
        once, and to render it multiple times with
        `ast_to_html`, links discovery and
        most of the link resolution being lazily done in that second phase.

        If you don't care about performance, you should simply
        use `translate`.

        Args:
            text: unicode, the docstring to parse.
            link_resolver: hotdoc.core.links.LinkResolver, an object
                which will be called to retrieve `hotdoc.core.links.Link`
                objects.

        Returns:
            capsule: A PyCapsule wrapping an opaque C pointer, which
                can be passed to `ast_to_html`
                afterwards.
            diagnostics: A list of diagnostics as output by the gtk-doc cmark
                extension
        """
        assert comment is not None

        text = comment.description

        if (self.remove_xml_tags or comment.filename in
                self.gdbus_codegen_sources):
            text = re.sub('<.*?>', '', text)

        if self.escape_html:
            # pylint: disable=deprecated-method
            text = cgi.escape(text)

        ast, diagnostics = cmark.gtkdoc_to_ast(text, link_resolver, include_resolver, comment.filename)

        for diag in diagnostics:
            if (comment.filename and comment.filename not in
                    self.gdbus_codegen_sources):
                # FIXME: update offset calculation code for includes
                if diag.filename != comment.filename:
                    diag.lineno = -1

                column = diag.column + comment.col_offset
                if diag.lineno == 0:
                    column += comment.initial_col_offset

                lines = text.split('\n')
                line = lines[diag.lineno]
                i = 0
                while line[i] == ' ':
                    i += 1
                column += i - 1

                if diag.lineno > 0 and any([c != ' ' for c in
                                            lines[diag.lineno - 1]]):
                    column += 1

                lineno = -1
                if comment.lineno != -1 and diag.lineno != -1:
                    lineno = (comment.lineno - 1 + comment.line_offset +
                              diag.lineno)
                warn(
                    diag.code,
                    message=diag.message,
                    filename=diag.filename,
                    lineno=lineno,
                    column=column)

        return ast

    # pylint: disable=no-self-use
    def ast_to_html(self, ast, link_resolver):
        """
        See the documentation of `to_ast` for
        more information.

        Args:
            ast: PyCapsule, a capsule as returned by `to_ast`
            link_resolver: hotdoc.core.links.LinkResolver, a link
                resolver instance.
        """
        out, _ = cmark.ast_to_html(ast, link_resolver)
        return out

    def translate_comment(self, comment, link_resolver, include_resolver):
        """
        Given a gtk-doc comment string, returns the comment translated
        to the desired format.
        """
        out = u''

        self.translate_tags(comment, link_resolver, include_resolver)
        ast = self.comment_to_ast(comment, link_resolver, include_resolver)
        out += self.ast_to_html(ast, link_resolver)
        return out

    def translate_tags(self, comment, link_resolver, include_resolver):
        """Banana banana
        """
        for tname in ('deprecated',):
            tag = comment.tags.get(tname)
            if tag is not None and tag.description:
                comment = comment_from_tag(tag)
                ast = self.comment_to_ast(comment, link_resolver, include_resolver)
                tag.description = self.ast_to_html(ast, link_resolver) or ''

    @staticmethod
    def add_arguments(parser):
        """Banana banana
        """
        group = parser.add_argument_group(
            'GtkDocStringFormatter', 'GtkDocStringFormatter options')
        group.add_argument("--gtk-doc-remove-xml", action="store_true",
                           dest="gtk_doc_remove_xml",
                           help="deprecated, use gdbus-codegen-sources")
        group.add_argument("--gtk-doc-escape-html", action="store_true",
                           dest="gtk_doc_esape_html", help="Escape html "
                           "in gtk-doc comments")
        group.add_argument("--gdbus-codegen-sources", action="store",
                           nargs='+', dest="gdbus_codegen_sources",
                           help=("files listed there will have all xml tags "
                                 "removed in their comments, and warnings "
                                 "will not be emitted for comment issues"))

    def parse_config(self, config):
        """Banana banana
        """
        self.remove_xml_tags = config.get('gtk_doc_remove_xml')
        self.escape_html = config.get('gtk_doc_escape_html')
        self.gdbus_codegen_sources = config.get_paths('gdbus_codegen_sources')


def parse_devhelp_index(dir_):
    path = os.path.join(dir_, os.path.basename(dir_) + '.devhelp2')
    if not os.path.exists(path):
        return False

    try:
        dh_root = etree.parse(path).getroot()
    except etree.Error:
        # No need to look for a sgml file
        return True

    online = dh_root.attrib.get('online')
    name = dh_root.attrib.get('name')
    author = dh_root.attrib.get('author')
    language = dh_root.attrib.get('language')

    if not online:
        if not name:
            return False
        online = 'https://developer.gnome.org/%s/unstable/' % name

    keywords = dh_root.findall('.//{http://www.devhelp.net/book}keyword')
    for kw in keywords:
        name = kw.attrib["name"]
        type_ = kw.attrib['type']
        link = kw.attrib['link']

        if type_ in ['macro', 'function']:
            name = name.rstrip(u' ()')
        elif type_ in ['struct', 'enum', 'union']:
            split = name.split(' ', 1)
            if len(split) == 2:
                name = split[1]
            else:
                name = split[0]
        elif type_ in ['signal', 'property']:
            # Heuristic to determine that the naming follows the gtk-doc "logic"
            if '#' in link and (language.lower() == 'c' or author == 'hotdoc'):
                anchor = link.split('#', 1)[1]
                if author == 'hotdoc':
                    name = anchor
                else:
                    split = anchor.split('-', 1)
                    if type_ == 'signal':
                        name = '%s::%s' % (split[0], split[1].lstrip('-'))
                    else:
                        name = '%s:%s' % (split[0], split[1].lstrip('-'))
        elif type_ in ['vfunc']:
            if '#' in link and (language.lower() == 'c' or author == 'hotdoc'):
                anchor = link.split('#', 1)[1]
                if author == 'hotdoc':
                    name = anchor
                    GTKDOC_HREFS[name.replace('::', '.')] = online + link

        GTKDOC_HREFS[name] = online + link

    return True


def parse_sgml_index(dir_):
    remote_prefix = ""
    n_links = 0
    path = os.path.join(dir_, "index.sgml")
    with open(path, 'r') as f:
        for l in f:
            if l.startswith("<ONLINE"):
                remote_prefix = l.split('"')[1]
            elif not remote_prefix:
                break
            elif l.startswith("<ANCHOR"):
                split_line = l.split('"')
                filename = split_line[3].split('/', 1)[-1]
                title = split_line[1].replace('-', '_')

                if title.endswith(":CAPS"):
                    title = title [:-5]
                if remote_prefix:
                    href = '%s/%s' % (remote_prefix, filename)
                else:
                    href = filename

                GTKDOC_HREFS[title] = href
                n_links += 1


def gather_links():
    global GATHERED_GTKDOC_LINKS

    if GATHERED_GTKDOC_LINKS:
        return

    GATHERED_GTKDOC_LINKS = True

    # XDG_DATA_DIRS is preference-ordered, we reverse so that preferred
    # links override less-preferred ones
    for datadir in reversed([XDG_DATA_HOME] + XDG_DATA_DIRS):
        for path in (os.path.join(datadir, 'devhelp', 'books'), os.path.join(datadir, 'gtk-doc', 'html')):
            if not os.path.exists(path):
                info("no gtk doc to gather links from in %s" % path)
                continue

            for node in os.listdir(path):
                dir_ = os.path.join(path, node)
                if os.path.isdir(dir_):
                    if not parse_devhelp_index(dir_):
                        try:
                            parse_sgml_index(dir_)
                        except IOError:
                            pass


def search_online_links(resolver, name):
    href = GTKDOC_HREFS.get(name)
    if href:
        return Link(href, name, name)
    return None

