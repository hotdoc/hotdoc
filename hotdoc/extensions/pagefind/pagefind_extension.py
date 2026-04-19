# -*- coding: utf-8 -*-
#
# Copyright © 2026 Thibault Saunier <tsaunier@igalia.com>
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
Builds a Pagefind (https://pagefind.app/) search index over the rendered
HTML output once the documentation has been fully generated.
"""

import asyncio
import os

from hotdoc.core.exceptions import HotdocException
from hotdoc.core.extension import Extension
from hotdoc.utils.loggable import Logger, info, warn

PNAME = 'pagefind'

DESCRIPTION = """
This extension runs Pagefind over the generated HTML output and ships
a client-side full-text search bundle under the ``_pagefind/`` directory.
"""

Logger.register_warning_code('pagefind-missing', HotdocException, domain=PNAME)
Logger.register_warning_code('pagefind-failed', HotdocException, domain=PNAME)


class PagefindExtension(Extension):
    extension_name = PNAME
    argument_prefix = PNAME
    connected = False

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group(
            'Pagefind', 'Client-side search powered by pagefind.app')
        group.add_argument('--disable-pagefind', action='store_true',
                           dest='disable_pagefind', default=False,
                           help='Skip building a Pagefind search index.')

    def setup(self):
        super().setup()

        if self.app.config.get('disable_pagefind', False):
            return

        if PagefindExtension.connected:
            return

        self.app.formatted_signal.connect(self.__build_index)
        PagefindExtension.connected = True

    # pylint: disable=no-self-use
    def __build_index(self, app):
        if not app.output:
            return

        html_dir = os.path.join(app.output, 'html')
        if not os.path.isdir(html_dir):
            return

        try:
            from pagefind.index import IndexConfig, PagefindIndex
        except ImportError as exc:
            warn('pagefind-missing',
                 'The "pagefind" Python package is not installed; '
                 'no search index will be built (%s).' % exc)
            return

        output_path = os.path.join(html_dir, 'pagefind')

        async def _run():
            config = IndexConfig(output_path=output_path)
            async with PagefindIndex(config=config) as index:
                await index.add_directory(html_dir)

        info('Building Pagefind index in %s' % output_path, PNAME)
        try:
            asyncio.run(_run())
        except Exception as exc:  # pylint: disable=broad-except
            warn('pagefind-failed',
                 'Pagefind indexing failed: %s' % exc)


def get_extension_classes():
    return [PagefindExtension]
