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
A set of languages with no external dependencies
"""

from hotdoc.extensions.gi.languages.javascript import (
    JavascriptLanguage)

from hotdoc.extensions.gi.languages.python import (
    PythonLanguage)

from hotdoc.extensions.gi.languages.c import (
    CLanguage)

def get_language_classes():
    """
    Hotdoc's setuptools entry point
    """
    res = [JavascriptLanguage, PythonLanguage, CLanguage]

    return res
