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

"""Base Hotdoc Exceptions"""

import io


class HotdocException(Exception):
    """Base Hotdoc exception"""


class InvalidPageMetadata(HotdocException):
    """Invalid page metadata"""


class ConfigError(HotdocException):
    """Banana banana"""
    pass


class ParsingException(HotdocException):
    """Banana banana"""
    pass


class BadInclusionException(HotdocException):
    """Banana banana"""
    pass


class InvalidOutputException(HotdocException):
    """Banana banana"""
    pass


def _format_source_exception(filename, message, lineno, column):
    from hotdoc.utils.loggable import TERMC
    with io.open(filename, 'r', encoding='utf-8') as _:
        text = _.read().expandtabs()
        lines = text.split('\n')

    res = []

    diag = ''
    diag += TERMC.BOLD
    if lineno != -1:
        diag += '%s:%d:%d: ' % (filename, lineno + 1, column + 1)
    else:
        diag += '%s: ' % (filename)
    diag += TERMC.NORMAL
    diag += message

    res.append(diag)

    if lineno != -1:
        for i in range(max(0, lineno - CONTEXT_HEIGHT),
                       min(len(lines), lineno + CONTEXT_HEIGHT + 1)):
            res.append('%05d:%s' % (i + 1, lines[i]))
            if i == lineno and column != -1:
                res.append(' ' * (column + 5) + TERMC.GREEN + '^' +
                           TERMC.NORMAL)

    return '\n'.join(res)


CONTEXT_HEIGHT = 2


class HotdocSourceException(HotdocException):
    """Banana banana"""
    def __init__(self, message=None, filename=None, lineno=-1, column=-1):
        if isinstance(message, str):
            message = message.decode('utf-8')
        self.filename = filename
        self.lineno = lineno
        self.column = column
        if filename:
            message = _format_source_exception(filename, message,
                                               lineno, column)
        super(HotdocSourceException, self).__init__(message)
