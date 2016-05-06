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

from hotdoc.utils.simple_signals import Signal

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


def find_md_file(filename, include_paths):
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
                included_content = '\n``` %s\n%s\n```\n' % (
                    lang, included_content)
            return included_content, lang


# pylint: disable=unused-argument
def add_md_includes(contents, source_file, include_paths=None, lineno=0):
    """
    Add includes from the @contents markdown and return the new patched content
    Args:
        contents: str, a markdown string
        source_file: str, the file from which @contents comes from
        include_paths: list, The list of include paths from the configuration
        lineno: int, The line number from which the content comes from in
            source_file
    """
    if include_paths is None:
        return contents

    inclusions = set(re.findall('{{(.+?)}}', contents))
    lang = None
    for inclusion in inclusions:
        include_filename, line_ranges, symbol = __parse_include(inclusion)
        if include_filename is None:
            continue

        # pylint: disable=no-member
        include_path = find_md_file(include_filename, include_paths)

        if include_path is None:
            continue

        included_content, lang = __get_content(include_path.strip(),
                                               line_ranges, symbol)

        # Recurse only if in markdown (otherwise we are in a code block)
        including = lang is "markdown"
        new_included_content = included_content
        while including:
            new_included_content = add_md_includes(new_included_content,
                                                   include_path, include_paths,
                                                   lineno)
            including = (new_included_content != included_content)
            included_content = new_included_content

        contents = contents.replace('{{' + inclusion + '}}', included_content)

    return contents
