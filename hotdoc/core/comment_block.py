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

import linecache
import os
from collections import defaultdict


# pylint: disable=too-few-public-methods
class TagValidator(object):
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


class Comment(object):
    """
    Code-parsing extensions should add instances of this class to
    DocDatabase.
    """
    # This constructor is convenient
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    def __init__(self, name=u'', title=None, params=None, filename=u'',
                 lineno=-1, endlineno=-1, annotations=None,
                 description=u'', short_description=None, tags=None,
                 raw_comment=u'', topics=None):
        self.name = name
        self.title = title
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
        self.description = unicode(description)
        self.short_description = short_description
        self.extension_attrs = defaultdict(lambda: defaultdict(dict))
        self.tags = tags or {}

        # FIXME : would be nicer to have the scanner do that ^^
        leading_ws = ''
        if lineno != -1:
            orig = linecache.getline(filename, lineno)
            leading_ws = (len(orig) - len(orig.lstrip(' '))) * ' '

        self.raw_comment = leading_ws + raw_comment

    def __getstate__(self):
        # Return a copy
        res = dict(self.__dict__)
        res['extension_attrs'] = None
        return res

    # pylint: disable=attribute-defined-outside-init
    def __setstate__(self, state):
        self.__dict__ = state
        self.extension_attrs = defaultdict(lambda: defaultdict(dict))


class Annotation(object):
    """
    An annotation is extra information that may or may not be displayed
    to the end-user, depending on the context.
    For example gobject annotations will be displayed for the
    C language, but hidden in python, and interpreted instead.
    """
    def __init__(self, name, argument=None):
        self.name = name
        self.argument = argument


class Tag(object):
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
                      description=tag.description,
                      annotations=tag.annotations)
    return comment
