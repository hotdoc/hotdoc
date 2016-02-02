"""
This module implements a Comment class, to be used
by code-parsing extensions.
"""

import linecache
import os


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
    def __init__(self, name='', title='', params=None, filename='',
                 lineno=-1, endlineno=-1, annotations=None,
                 description='', short_description='', tags=None,
                 raw_comment=''):
        self.name = name
        self.title = title
        self.params = params or {}
        self.filename = os.path.abspath(filename)
        self.lineno = lineno
        self.endlineno = endlineno
        self.annotations = annotations or {}
        self.description = description
        self.short_description = short_description
        self.tags = tags or {}

        # FIXME : would be nicer to have the scanner do that ^^
        leading_ws = ''
        if lineno != -1:
            orig = linecache.getline(filename, lineno)
            leading_ws = (len(orig) - len(orig.lstrip(' '))) * ' '

        self.raw_comment = leading_ws + raw_comment


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
        self.description = description
        self.value = value
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
