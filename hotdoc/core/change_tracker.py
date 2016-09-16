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
Defines and tests ChangeTracker
"""

import os
from collections import defaultdict

from hotdoc.utils.utils import OrderedSet, get_mtime


class ChangeTracker(object):
    """
    This class should only be instantiated and used through
    the main `DocRepo` instance.

    It provides with modification time tracking and some
    other utilities.
    """
    all_stale_files = set()
    all_unlisted_files = set()

    def __init__(self):
        self.exts_mtimes = {}
        self.hard_deps_mtimes = {}
        self.mtimes = defaultdict(defaultdict)

    def get_stale_files(self, all_files, fileset_name):
        """
        Banana banana
        """
        stale = OrderedSet()

        previous_mtimes = self.mtimes[fileset_name]
        new_mtimes = defaultdict()

        for filename in all_files:
            mtime = get_mtime(filename)
            prev_mtime = previous_mtimes.pop(filename, None)
            new_mtimes[filename] = mtime
            if mtime == prev_mtime:
                continue

            stale.add(filename)

        self.mtimes[fileset_name] = new_mtimes

        unlisted = set(previous_mtimes.keys())

        ChangeTracker.all_stale_files |= stale
        ChangeTracker.all_unlisted_files |= unlisted

        return stale, unlisted

    def add_hard_dependency(self, filename):
        """
        Banana banana
        """
        mtime = get_mtime(filename)

        if mtime != -1:
            self.hard_deps_mtimes[filename] = mtime

    def hard_dependencies_are_stale(self):
        """
        Banana banana
        """
        for filename, last_mtime in self.hard_deps_mtimes.items():
            mtime = get_mtime(filename)

            if mtime == -1 or mtime != last_mtime:
                return True

        return False

if __name__ == '__main__':
    CTRACKER = ChangeTracker()

    # Initial build
    os.system('touch a b c d')
    print "Should be ([a, b, c, d], [])"
    print CTRACKER.get_stale_files(['a', 'b', 'c', 'd'], 'testing')

    # Build where nothing changed
    print "Should be ([], [])"
    print CTRACKER.get_stale_files(['a', 'b', 'c', 'd'], 'testing')

    # Build with two files changed
    os.system('touch b d')
    print "Should be ([b, d], [])"
    print CTRACKER.get_stale_files(['a', 'b', 'c', 'd'], 'testing')

    # Build where one file was removed
    os.system('rm -f b')
    print "Should be ([b], [])"
    print CTRACKER.get_stale_files(['a', 'b', 'c', 'd'], 'testing')
    print "Should be ([], [])"
    print CTRACKER.get_stale_files(['a', 'b', 'c', 'd'], 'testing')

    # Build where one file was unlisted
    print "Should be ([], [a])"
    print CTRACKER.get_stale_files(['b', 'c', 'd'], 'testing')

    # Build with file listed again
    print "Should be ([a], [])"
    print CTRACKER.get_stale_files(['a', 'b', 'c', 'd'], 'testing')

    os.system('rm -f a b c d')
