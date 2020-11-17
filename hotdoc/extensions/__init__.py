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

import sys

from hotdoc.extensions.syntax_highlighting.syntax_extension import (
    SyntaxHighlightingExtension)
from hotdoc.extensions.search.search_extension import SearchExtension
from hotdoc.extensions.tags.tag_extension import TagExtension
from hotdoc.extensions.devhelp.devhelp_extension import DevhelpExtension
from hotdoc.extensions.license.license_extension import LicenseExtension
from hotdoc.extensions.check_since_markers.check_since_markers import CheckMissingSinceMarkersExtension
from hotdoc.extensions.git_upload.git_upload_extension import (
    GitUploadExtension)
from hotdoc.extensions.edit_on_github.edit_on_github_extension import (
    EditOnGitHubExtension)
from hotdoc.extensions.comment_on_github.comment_on_github_extension import (
    CommentOnGithubExtension)

if sys.version_info[1] >= 5:
    from hotdoc.extensions.dbus.dbus_extension import DBusExtension


def get_extension_classes():
    """
    Hotdoc's setuptools entry point
    """
    res = [SyntaxHighlightingExtension, SearchExtension, TagExtension,
           DevhelpExtension, LicenseExtension, GitUploadExtension,
           EditOnGitHubExtension, CheckMissingSinceMarkersExtension,
           CommentOnGithubExtension]

    if sys.version_info[1] >= 5:
        res += [DBusExtension]

    try:
        from hotdoc.extensions.c.c_extension import CExtension
        res += [CExtension]
    except ImportError:
        pass

    try:
        from hotdoc.extensions.gi.gi_extension import GIExtension
        res += [GIExtension]
    except ImportError:
        pass

    try:
        from hotdoc.extensions.gst.gst_extension import GstExtension
        res += [GstExtension]
    except ImportError:
        pass

    return res
