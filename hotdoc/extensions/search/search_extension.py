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

# pylint: disable=missing-docstring

import os
import shutil
import multiprocessing
from lxml import etree
from hotdoc.parsers import search
from hotdoc.core.extension import Extension
from hotdoc.utils.setup_utils import symlink

DESCRIPTION =\
    """
This extension enables client-side full-text search
for html documentation produced by hotdoc.
"""

HERE = os.path.dirname(__file__)


class SearchExtension(Extension):
    extension_name = 'search'
    connected = False

    __connected_all_projects = False

    def __init__(self, app, project):
        Extension.__init__(self, app, project)
        self.__all_paths = []
        self.script = os.path.abspath(os.path.join(HERE, 'trie.js'))

    def setup(self):
        super(SearchExtension, self).setup()

        for ext in self.project.extensions.values():
            ext.formatter.formatting_page_signal.connect(
                self.__formatting_page)

        if not SearchExtension.connected:
            self.app.formatted_signal.connect(self.__build_index)
            for ext in self.app.project.extensions.values():
                ext.formatter.writing_page_signal.connect(
                    self.__writing_page_cb)
            SearchExtension.connected = True

    def __connect_to_subprojects(self, project, toplevel=False):
        if not toplevel:
            for ext in project.extensions.values():
                ext.formatter.writing_page_signal.connect(
                    self.__writing_page_cb)

        for subproj in project.subprojects.values():
            self.__connect_to_subprojects(subproj)

    def __writing_page_cb(self, formatter, page, path, lxml_tree):
        if not SearchExtension.__connected_all_projects:
            self.__connect_to_subprojects(self.project, toplevel=True)
            SearchExtension.__connected_all_projects = True

        self.__all_paths.append (path)

    def __build_index(self, app):  # pylint: disable=unused-argument
        html_dir = os.path.join(self.app.output, 'html')
        search_dir = os.path.join(html_dir, 'assets', 'js', 'search')
        fragments_dir = os.path.join(search_dir, 'hotdoc_fragments')

        all_rel_paths = [os.path.relpath(p, html_dir) for p in self.__all_paths]

        search.create_index(all_rel_paths, multiprocessing.cpu_count() + 1, search_dir,
                fragments_dir, html_dir, self.app.project.get_private_folder(),
                os.path.join(HERE, 'stopwords.txt'))

        subdirs = next(os.walk(html_dir))[1]
        subdirs.append(html_dir)

        dumped_trie_path = os.path.join(html_dir, 'dumped.trie')
        # pylint: disable=unused-variable
        for root, dirs, files in os.walk(html_dir):
            for dir_ in dirs:
                if dir_ == 'assets':
                    continue
                dest_trie = os.path.join(root, dir_, 'dumped.trie')
                try:
                    os.remove(dest_trie)
                except OSError:
                    pass

                symlink(os.path.relpath(
                    dumped_trie_path, os.path.join(root, dir_)), dest_trie)

    # pylint: disable=unused-argument
    def __formatting_page(self, formatter, page):
        page.output_attrs['html']['scripts'].add(self.script)


def get_extension_classes():
    return [SearchExtension]
