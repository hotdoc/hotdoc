# -*- coding: utf-8 -*-
#
# Copyright 2019 Collabora Ltd
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
Baseclass for languages
"""
import os
from collections import OrderedDict

from hotdoc.utils.configurable import Configurable

# FIXME: Avoid the use of a global dictionary
FUNDAMENTALS = {}
ALIASES = {}

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class Language(Configurable):
    """
    All languages should inherit from this base class

    Attributes:
        language_name: str, the unique name of this extension, should
            be overriden.
    """
    # pylint: disable=unused-argument
    language_name = "base-language"

    def __init__(self):
        """Constructor for `Language`.

        This should never get called directly.
        """
        if not self.language_name in ALIASES:
            ALIASES[self.language_name] = {}

    def get_fundamental(self, name):
        """
        Get the Link for the specified fundamental
        Extension subclasses might implement this.
        """
        return FUNDAMENTALS[self.language_name].get(name)

    @classmethod
    def add_fundamental(cls, name, link):
        """
        Add a Link for the specified fundamental
        Extension subclasses might implement this.
        """
        FUNDAMENTALS[cls.language_name][name] = link

    def make_translations(self, unique_name, node):
        """
        Extension subclasses should implement this to compute and
        store the title that should be displayed when linking to a
        given unique_name, eg in python when linking to
        test_greeter_greet() we want to display Test.Greeter.greet
        """
        raise NotImplementedError

    def get_translation(self, unique_name):
        """
        Extension subclasses should implement this.
        See make_translations
        """
        raise NotImplementedError

    def get_alias_link(self, name):
        """
        Get the alias link for the given name
        Extension subclasses might implement this.
        """
        aliased_type = ALIASES[self.language_name].get(name)
        if aliased_type:
            return aliased_type.type_link
        return None

    def add_alias_type(self, name, alias_type):
        """
        Add the alias Link for the given name
        Extension subclasses might implement this.
        """
        ALIASES[self.language_name][name] = alias_type

    @staticmethod
    def get_dependencies():
        """
        Override this to return the list of extensions this language
        depends on if needed.

        Returns:
            list: A list of `ExtDependency` instances.
        """
        return []
