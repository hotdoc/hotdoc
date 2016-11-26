#!/usr/bin/python
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

"""Banana banana
"""

import traceback

from hotdoc.core.project import Project
from hotdoc.core.exceptions import HotdocException
from hotdoc.utils.loggable import Logger


def run(args):
    """
    Banana banana
    """
    res = 0
    project = Project()

    # pylint: disable=broad-except
    try:
        project.load_command_line(args)
        project.setup()
        project.format()
        project.persist()
    except HotdocException:
        res = len(Logger.get_issues())
    except Exception:
        print("An unknown error happened while building the documentation"
              " and hotdoc cannot recover from it. Please report "
              "a bug with this error message and the steps to "
              "reproduce it")
        traceback.print_exc()
        res = 1
    finally:
        project.finalize()

    return res
