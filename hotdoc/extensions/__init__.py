# -*- coding: utf-8 -*-
#
# Copyright © 2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2016 Collabora Ltd
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
A set of extensions with no external dependencies
"""

from hotdoc.extensions.syntax_highlighting.syntax_extension import (
    SyntaxHighlightingExtension)
from hotdoc.extensions.search.search_extension import SearchExtension
from hotdoc.extensions.tags.tag_extension import TagExtension
from hotdoc.extensions.devhelp.devhelp_extension import DevhelpExtension
from hotdoc.extensions.license.license_extension import LicenseExtension


def get_extension_classes():
    """
    Hotdoc's setuptools entry point
    """
    return [SyntaxHighlightingExtension, SearchExtension, TagExtension,
            DevhelpExtension, LicenseExtension]
