# -*- coding: utf-8 -*-
#
# Copyright © 2016 Thibault Saunier <thibault.saunier@opencreed.com>
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
The markdown file including system
"""
import re
import os

from hotdoc.utils.signals import Signal

# pylint: disable=invalid-name
# pylint: disable=pointless-string-statement
"""
Signal emitted to retrieve included content.

Args:
    include_path: str: The path of the file to include from
    line_ranges: list(str): The ranges of the lines to include from
    symbol: str: The name of the symbol to include

Returns a 2 tuple containing the included content and the lang it is in.

Returns:
    str: The content to be included
    str: The lang of the content ('' means unknown but not markdown)
"""
include_signal = Signal()


def find_file(filename, include_paths):
    """Banana banana
    """
    if os.path.isabs(filename):
        if os.path.exists(filename):
            return filename
        return None

    for include_path in include_paths:
        fpath = os.path.join(include_path, filename)
        if os.path.exists(fpath) and os.path.isfile(fpath):
            return fpath

    return None


def __parse_include(include):
    include = include.strip()
    line_ranges_str = re.findall(r'\[([0-9]+?):([0-9]+?)\]', include)

    if len(line_ranges_str) != len(re.findall(r'\[(.+?):(.+?)\]', include)):
        return None, None, None

    line_ranges = []
    for s, e in line_ranges_str:
        line_ranges.append((int(s), int(e)))

    include = re.sub(r'\[(.+?):(.+?)\]', "", include)
    try:
        symbol = re.findall(r'#(.+?)$', include)[0]
    except IndexError:
        symbol = None

    include_filename = re.sub(r'#.*$', "", include)

    return (include_filename, line_ranges, symbol)


def __get_content(include_path, line_ranges, symbol):
    for c in include_signal(include_path, line_ranges, symbol):
        if c is not None:
            included_content, lang = c
            if lang != "markdown":
                included_content = u'\n``` %s\n%s\n```\n' % (
                    lang, included_content)
            return included_content
    return None


def resolve(uri, include_paths):
    """
    Banana banana
    """
    include_filename, line_ranges, symbol = __parse_include(uri)
    if include_filename is None:
        return None
    include_path = find_file(include_filename, include_paths)
    if include_path is None:
        return None
    return __get_content(include_path.strip(),
                         line_ranges, symbol)
