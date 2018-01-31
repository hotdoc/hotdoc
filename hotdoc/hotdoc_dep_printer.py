#!/usr/bin/python
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

"""A helper tool for hotdoc build system integration.
"""

import sys

from hotdoc.core.config import ConfigParser

def main():
    if len(sys.argv) != 2:
        print "USAGE: %s path/to/conf/file" % sys.argv[0]
        sys.exit(1)

    PARSER = ConfigParser(conf_file=sys.argv[1])
    PARSER.print_make_dependencies()
    sys.exit(0)
