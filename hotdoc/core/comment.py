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
This module implements a Comment class, to be used
by code-parsing extensions.
"""
import os
from collections import defaultdict


# pylint: disable=too-few-public-methods
class TagValidator:
    """
    Tag validators may be created by extensions that wish
    to add custom tags. (Returns, Since, etc...)
    """

    def __init__(self, name):
        self.name = name

    def validate(self, value):
        """
        Subclasses should implement this to validate the
        value of a tag.
        """
        raise NotImplementedError


class Comment:
    """
    Represents a piece of markup text, optionally tied to a particular symbol.
    Code-parsing extensions should add instances of this class to
    Database.

    Args:
        name (str): Unique name for the symbol that this comment refers to.
        title (Comment): Another comment containing the display name of the
            symbol that this comment refers to.
        params (dict): FIXME
        filename (str): Path to source file containing this comment.
        lineno (int): Line number where this comment starts.
        endlineno (int): Line number where this comment ends.
        annotations (dict): FIXME
        tags (dict): FIXME
        raw_comment (str): The text of the comment as it appears in the source
            file.
        topics (dict): FIXME
        meta (dict): Metadata
    """
    # This constructor is convenient
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals

    def __init__(self, name=u'', title=None, params=None, filename=u'',
                 lineno=-1, endlineno=-1, annotations=None,
                 tags=None, raw_comment=u'', topics=None, meta=None,
                 description=None, short_description=None, toplevel=False):
        self.name = name
        self.params = params or {}
        self.topics = topics or {}
        if filename:
            self.filename = os.path.abspath(filename)
        else:
            self.filename = None
        self.lineno = lineno
        self.endlineno = endlineno
        self.line_offset = 0
        self.col_offset = 0
        self.initial_col_offset = 0
        self.annotations = annotations or {}

        meta = self.__cleanup_meta(meta)
        self.description = description or meta.get('description', '')
        if title:
            self.title = title
        elif meta.get('title'):
            self.title = Comment(name='title',
                                 description=meta.get('title'))
        else:
            self.title = None

        if short_description:
            self.short_description = short_description
        elif meta.get('short_description'):
            self.short_description = Comment(name='short_description',
                                             description=meta.get('short_description'))
        else:
            self.short_description = ''

        self.extension_attrs = defaultdict(lambda: defaultdict(dict))
        self.tags = tags or {}
        self.meta = meta or {}
        self.raw_comment = raw_comment
        self.toplevel = toplevel

    @staticmethod
    def __cleanup_meta(meta):
        cleaned_meta = {}
        for key, value in (meta or {}).items():
            cleaned_meta[key.replace('_', '-').lower()] = value
        return cleaned_meta

    def __getstate__(self):
        # Return a copy
        res = dict(self.__dict__)
        res['extension_attrs'] = None
        return res

    # pylint: disable=attribute-defined-outside-init
    def __setstate__(self, state):
        self.__dict__ = state
        self.extension_attrs = defaultdict(lambda: defaultdict(dict))


class Annotation:
    """
    An annotation is extra information that may or may not be displayed
    to the end-user, depending on the context.
    For example gobject annotations will be displayed for the
    C language, but hidden in python, and interpreted instead.
    """

    def __init__(self, name, argument=None):
        self.name = name
        self.argument = argument


class Tag:
    """
    A tag is extra information that shall always be displayed
    to the end-user, independent of the context.
    For example, since tags or return tags.
    """

    def __init__(self, name, description, value=None, annotations=None):
        self.name = name
        self.description = description or ''
        self.value = value or ''
        self.annotations = annotations or {}


def comment_from_tag(tag):
    """
    Convenience function to create a full-fledged comment for a
    given tag, for example it is convenient to assign a Comment
    to a ReturnValueSymbol.
    """
    if not tag:
        return None
    comment = Comment(name=tag.name,
                      meta={'description': tag.description},
                      annotations=tag.annotations)
    return comment
