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
Implement a parser for standalone markdown pages,
and for sitemap files.
"""

import io
from collections import OrderedDict

from hotdoc.core.exceptions import HotdocSourceException
from hotdoc.utils.loggable import error, Logger
from hotdoc.utils.utils import dedent, dequote, IndentError


class SitemapDuplicateError(HotdocSourceException):
    """
    Raised when the same file was listed multiple times in
    a sitemap file.
    """
    pass


class SitemapError(HotdocSourceException):
    """
    Generic sitemap error.
    """
    pass


Logger.register_error_code('bad-indent', IndentError, domain='sitemap')
Logger.register_error_code('sitemap-duplicate', SitemapDuplicateError,
                           domain='sitemap')
Logger.register_error_code('sitemap-error', SitemapError,
                           domain='sitemap')


# pylint: disable=too-few-public-methods
class StandaloneParser(object):
    """
    Banana banana
    """
    pass


class Sitemap(object):
    """
    Represents the desired hierarchy of the generated output.

    Attributes:
        index_file: str, the path to the index file.
    """

    def __init__(self, root, source_file, index_file, source_map):
        self.__root = root
        self.__source_map = source_map
        self.source_file = source_file
        self.index_file = index_file
        self.__all_sources = None

    def walk(self, action, user_data=None):
        """
        Walk the hierarchy, applying action to each filename.

        Args:
            action: callable, the callable to invoke for each filename,
                will be invoked with the filename, the subfiles, and
                the level in the sitemap.
        """
        action(self.index_file, self.__root, 0, user_data)
        self.__do_walk(self.__root, 1, action, user_data)

    def __store_one(self, source_file, subpages, level, list_):
        list_.append((source_file, level))

    def __iter__(self):
        list_ = []
        self.walk(self.__store_one, user_data=list_)
        for elem in list_:
            yield elem

    def _dump(self):
        self.walk(self.__dump_one)

    def get_all_sources(self):
        """
        Returns:
            OrderedDict: all source file names in the hierarchy, paired with
                the names of their subpages.
        """
        if self.__all_sources is None:
            self.__all_sources = OrderedDict()
            self.walk(self.__add_one)
        return self.__all_sources

    def get_position(self, source_file):
        return self.__source_map.get(source_file)

    def get_subpages(self, source_file):
        """
        Args:
            str: name of the source file for which to retrieve subpages.
        Returns:
            OrderedDict: The subpages of `source_file`
        """
        return self.get_all_sources()[source_file]

    def __add_one(self, source_file, subpages, _, __):
        self.__all_sources[source_file] = list(subpages.keys())

    # pylint: disable=no-self-use
    def __dump_one(self, source_file, _, level, __):
        print(level * '\t' + source_file)

    def __do_walk(self, parent, level, action, user_data=None):
        for source_file, subpages in list(parent.items()):
            action(source_file, subpages, level, user_data)
            self.__do_walk(subpages, level + 1, action, user_data)


class SitemapParser(object):
    """
    Implements parsing of sitemap files, to generate `Sitemap` objects.
    """
    # pylint: disable=too-many-locals
    # pylint: disable=no-self-use

    def parse(self, filename):
        """
        Parse a sitemap file.

        Args:
            filename: str, the path to the sitemap file.

        Returns:
            Sitemap: the generated sitemap.
        """
        with io.open(filename, 'r', encoding='utf-8') as _:
            lines = _.readlines()

        all_source_files = set()
        source_map = {}

        lineno = 0
        root = None
        index = None
        cur_level = -1
        parent_queue = []

        for line in lines:
            try:
                level, line = dedent(line)
                if line.startswith('#'):
                    lineno += 1
                    continue
                elif line.startswith('\\#'):
                    line = line[1:]
            except IndentError as exc:
                error('bad-indent', 'Invalid indentation', filename=filename,
                      lineno=lineno, column=exc.column)

            if not line:
                lineno += 1
                continue

            source_file = dequote(line)

            if not source_file:
                lineno += 1
                continue

            if source_file in all_source_files:
                error('sitemap-duplicate', 'Filename listed twice',
                      filename=filename, lineno=lineno, column=level * 8 + 1)

            all_source_files.add(source_file)
            source_map[source_file] = (lineno, level * 8 + 1)

            page = OrderedDict()

            if root is not None and level == 0:
                error('sitemap-error', 'Sitemaps only support one root',
                      filename=filename, lineno=lineno, column=0)

            if root is None:
                root = page
                index = source_file
            else:
                lvl_diff = cur_level - level
                while lvl_diff >= 0:
                    parent_queue.pop()
                    lvl_diff -= 1

                parent_queue[-1][source_file] = page

            parent_queue.append(page)

            cur_level = level

            lineno += 1

        return Sitemap(root, filename, index, source_map)
