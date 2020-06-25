# -*- coding: utf-8 -*-
#
# Copyright © 2020 Thibault Saunier <tsaunier@igalia.com>
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

import json
from hotdoc.core.exceptions import HotdocSourceException
from hotdoc.utils.loggable import Logger, warn
from hotdoc.core.extension import Extension

DESCRIPTION =\
    """
This extension allows to warn about missing `Since` markers in newly added
API.
"""


Logger.register_warning_code('missing-since-marker', HotdocSourceException,
                             'check-missing-since-markers')


class CheckMissingSinceMarkersExtension(Extension):
    extension_name = 'check-missing-since-markers'

    def __init__(self, app, project):
        Extension.__init__(self, app, project)
        self.__symbols_database = None

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('since-markers-check-extension',
                                          DESCRIPTION)
        group.add_argument("--previous-symbol-index")

    def parse_toplevel_config(self, config):
        self.__symbols_database = config.get_index(prefix="previous_symbol")

    def setup(self):
        if self.__symbols_database:
            self.app.formatted_signal.connect_after(self.__check_since_markers)

    def __check_has_since(self, sym):
        since = ""
        if sym.comment:
            since_v = sym.comment.tags.get("since")
            if since_v:
                since = since_v.value
        return since

    def __add_children_with_since(self, inherited_sinces, sym):
        for child in sym.get_children_symbols():
            if child is None:
                continue
            inherited_sinces.add(child)
            self.__add_children_with_since(inherited_sinces, child)

    def __check_since_markers(self, app):
        with open(self.__symbols_database) as f:
            prev_symbols = set(json.load(f))

        all_symbols = app.database.get_all_symbols()
        inherited_sinces = set()
        missing_since_syms = set()
        for name, sym in all_symbols.items():
            if name in prev_symbols:
                continue

            if not self.__check_has_since(sym):
                missing_since_syms.add(sym)
            else:
                self.__add_children_with_since(inherited_sinces, sym)

        for sym in missing_since_syms - inherited_sinces:
            if sym.comment and sym.comment.filename:
                filename = sym.comment.filename
                lineno = sym.comment.endlineno - 1
            else:
                filename = sym.filename
                lineno = sym.lineno

            warn('missing-since-marker',
                    message="Missing since marker for %s" % sym.unique_name,
                    filename=filename,
                    lineno=lineno,
                    )


def get_extension_classes():
    return [CheckMissingSinceMarkersExtension]
