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

from hotdoc.core.formatter import Formatter
from hotdoc.core.extension import Extension

from hotdoc.utils.utils import recursive_overwrite
from hotdoc.utils.loggable import warn, Logger
from hotdoc.core.exceptions import ConfigError

DESCRIPTION = """
This extension uses prism to syntax highlight code
snippets.
"""


HERE = os.path.dirname(__file__)


Logger.register_warning_code('syntax-invalid-theme', ConfigError,
                             'syntax-extension')


class SyntaxHighlightingExtension(Extension):
    """
    The actual syntax highlighting implementation
    """
    extension_name = 'syntax-highlighting-extension'
    argument_prefix = 'syntax-highlighting'

    def __init__(self, app, project):
        Extension.__init__(self, app, project)
        self.__asset_folders = set()
        self.activated = False

    def __formatting_page_cb(self, formatter, page):
        prism_theme = Formatter.theme_meta.get('prism-theme', 'prism')
        prism_theme_path = '%s.css' % os.path.join(HERE, 'prism', 'themes', prism_theme)

        if os.path.exists(prism_theme_path):
            page.output_attrs['html']['stylesheets'].add(prism_theme_path)
        else:
            warn('syntax-invalid-theme', 'Prism has no theme named %s' %
                 prism_theme)

        page.output_attrs['html']['scripts'].add(
            os.path.join(HERE, 'prism', 'components', 'prism-core.js'))
        page.output_attrs['html']['scripts'].add(
            os.path.join(HERE, 'prism', 'plugins', 'autoloader',
                         'prism-autoloader.js'))
        page.output_attrs['html']['scripts'].add(
            os.path.join(HERE, 'prism_autoloader_path_override.js'))

        folder = os.path.join('html', 'assets', 'prism_components')
        self.__asset_folders.add(folder)

    def __formatted_cb(self, project):
        ipath = os.path.join(HERE, 'prism', 'components')
        for folder in self.__asset_folders:
            opath = os.path.join(self.app.output, folder)
            recursive_overwrite(ipath, opath)

    def setup(self):
        super(SyntaxHighlightingExtension, self).setup()
        if not self.activated:
            return

        for ext in self.project.extensions.values():
            ext.formatter.formatting_page_signal.connect(
                self.__formatting_page_cb)
        self.project.formatted_signal.connect(self.__formatted_cb)

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('Syntax highlighting extension',
                                          DESCRIPTION)
        group.add_argument('--disable-syntax-highlighting',
                           action="store_true",
                           help="Deactivate the syntax highlighting extension",
                           dest='disable_syntax_highlighting')

    def parse_config(self, config):
        super(SyntaxHighlightingExtension, self).parse_config(config)
        self.activated = \
            not bool(config.get('disable_syntax_highlighting', False))
