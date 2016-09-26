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

"""
A syntax highlighting module
"""

import os

from hotdoc.core.base_extension import BaseExtension
from hotdoc.core.base_formatter import Formatter

from hotdoc.utils.utils import recursive_overwrite

DESCRIPTION = """
This extension uses prism to syntax highlight code
snippets.
"""


HERE = os.path.dirname(__file__)


class SyntaxHighlightingExtension(BaseExtension):
    """
    The actual syntax highlighting implementation
    """
    extension_name = 'syntax-highlighting-extension'
    argument_prefix = 'syntax-highlighting'
    activated = False

    def __init__(self, doc_repo):
        BaseExtension.__init__(self, doc_repo)
        self.__asset_folders = set()

    def __formatting_page_cb(self, formatter, page):
        page.output_attrs['html']['stylesheets'].add(
            os.path.join(HERE, 'prism', 'themes', 'prism.css'))

        page.output_attrs['html']['scripts'].add(
            os.path.join(HERE, 'prism', 'components', 'prism-core.js'))
        page.output_attrs['html']['scripts'].add(
            os.path.join(HERE, 'prism', 'plugins', 'autoloader',
                         'prism-autoloader.js'))
        page.output_attrs['html']['scripts'].add(
            os.path.join(HERE, 'prism_autoloader_path_override.js'))

        folder = os.path.join(formatter.get_output_folder(), 'assets',
                              'prism_components')
        self.__asset_folders.add(folder)

    def __formatted_cb(self, doc_repo):
        ipath = os.path.join(HERE, 'prism', 'components')
        for folder in self.__asset_folders:
            opath = os.path.join(doc_repo.output, folder)
            recursive_overwrite(ipath, opath)

    def setup(self):
        if not SyntaxHighlightingExtension.activated:
            return

        Formatter.formatting_page_signal.connect(self.__formatting_page_cb)
        self.doc_repo.formatted_signal.connect(self.__formatted_cb)

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('Syntax highlighting extension',
                                          DESCRIPTION)
        group.add_argument('--syntax-highlighting-activate',
                           action="store_true",
                           help="Activate the syntax highlighting extension",
                           dest='syntax_highlighting_activate')

    @staticmethod
    def parse_config(doc_repo, config):
        SyntaxHighlightingExtension.activated = \
            bool(config.get('syntax_highlighting_activate', False))
