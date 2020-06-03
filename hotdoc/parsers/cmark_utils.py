#!/usr/bin/env python
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
This module implements some utils for the cmark C module.
"""


# pylint: disable=too-few-public-methods
class CMarkDiagnostic(object):
    """
    A simple diagnostic class to be instantiated by the cmark C module
    """

    def __init__(self, code, message, lineno, column, filename):
        self.code = code
        self.message = message
        self.lineno = lineno
        self.column = column
        self.filename = filename
