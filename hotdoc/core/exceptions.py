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

from hotdoc.utils.loggable import Logger


class HotdocException(Exception):
    """Base Hotdoc exception"""


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


Logger.register_error_code('invalid-config', ConfigError)
Logger.register_error_code('setup-issue', ConfigError)
Logger.register_warning_code('parsing-issue', ParsingException)
