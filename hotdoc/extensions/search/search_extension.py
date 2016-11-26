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
from hotdoc.core.extension import Extension
from hotdoc.core.doc_tree import Page
from hotdoc.extensions.search.create_index import SearchIndex

DESCRIPTION =\
    """
This extension enables client-side full-text search
for html documentation produced by hotdoc.
"""

HERE = os.path.dirname(__file__)


def list_html_files(root_dir, exclude_dirs):
    html_files = []
    for root, dirs, files in os.walk(root_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for _ in files:
            if _.endswith(".html"):
                html_files.append(os.path.join(root, _))

    return html_files


class SearchExtension(Extension):
    extension_name = 'search'

    def __init__(self, project):
        Extension.__init__(self, project)
        project.formatted_signal.connect(self.__build_index)
        self.enabled = False
        self.script = os.path.abspath(os.path.join(HERE, 'trie.js'))

    def setup(self):
        self.enabled = self.project.output_format == 'html'
        Page.formatting_signal.connect(self.__formatting_page)

    def __build_index(self, project):
        # FIXME
        if self.project.incremental:
            return

        formatter = project.extensions['core'].get_formatter('html')
        output = os.path.join(project.output, formatter.get_output_folder())

        assets_path = os.path.join(output, 'assets')
        dest = os.path.join(assets_path, 'js')

        topdir = os.path.abspath(os.path.join(assets_path, '..'))

        subdirs = next(os.walk(topdir))[1]
        subdirs.append(topdir)

        exclude_dirs = ['assets']
        sources = list_html_files(output, exclude_dirs)
        stale, unlisted = self.get_stale_files(sources)

        stale |= unlisted

        if not stale:
            return

        index = SearchIndex(output, dest,
                            self.project.get_private_folder())
        index.scan(stale)

        for subdir in subdirs:
            if subdir == 'assets':
                continue
            shutil.copyfile(os.path.join(self.project.get_private_folder(),
                                         'search.trie'),
                            os.path.join(topdir, subdir, 'dumped.trie'))

    def __formatting_page(self, page, _):
        page.output_attrs['html']['scripts'].add(self.script)


def get_extension_classes():
    return [SearchExtension]
