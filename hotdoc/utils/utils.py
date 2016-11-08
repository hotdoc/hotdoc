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
Toolbox
"""

import collections
import os
import shutil
import math
import sys
import subprocess
import re

import pkg_resources
from toposort import toposort_flatten

from hotdoc.core.exceptions import HotdocSourceException
from hotdoc.utils.setup_utils import symlink

WIN32 = (sys.platform == 'win32')


def splitall(path):
    """
    Splits path in its components:
    foo/bar, /foo/bar and /foo/bar/ will all return
    ['foo', 'bar']
    """
    head, tail = os.path.split(os.path.normpath(path))
    components = []
    while len(tail) > 0:
        components.insert(0, tail)
        head, tail = os.path.split(head)
    return components


def recursive_overwrite(src, dest, ignore=None):
    """
    Banana banana
    """
    if os.path.islink(src):
        linkto = os.readlink(src)
        symlink(linkto, dest)
    elif os.path.isdir(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        files = os.listdir(src)
        if ignore is not None:
            ignored = ignore(src, files)
        else:
            ignored = set()
        for _ in files:
            if _ not in ignored:
                recursive_overwrite(os.path.join(src, _),
                                    os.path.join(dest, _),
                                    ignore)
    else:
        shutil.copyfile(src, dest)


def count_folders(path):
    """
    Returns the number of folders in a path string, excluding
    the filename.
    Note: 'foo/bar/' will return 1
    """
    return max(0, len(splitall(path)) - 1)


def all_subclasses(cls):
    """
    Banana banana
    """
    return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                   for g in all_subclasses(s)]


def get_mtime(filename):
    """
    Banana banana
    """
    try:
        stat = os.stat(filename)
    except OSError:
        return -1

    # Check the modification time.  We need to adjust on Windows.
    mtime = stat.st_mtime
    if WIN32:
        mtime -= stat.st_ctime

    return mtime


def get_extra_extension_classes(paths):
    """
    Banana banana
    """
    extra_classes = {}
    wset = pkg_resources.WorkingSet([])
    distributions, _ = wset.find_plugins(pkg_resources.Environment(paths))

    for dist in distributions:
        sys.path.append(dist.location)
        wset.add(dist)

    for entry_point in wset.iter_entry_points(group='hotdoc.extensions',
                                              name='get_extension_classes'):
        try:
            activation_function = entry_point.load()
            classes = activation_function()
        # pylint: disable=broad-except
        except Exception as _:
            print "Failed to load %s" % entry_point.module_name, _
            continue

        for klass in classes:
            extra_classes[klass.extension_name] = klass

    return extra_classes


def get_installed_extension_classes(sort):
    """
    Banana banana
    """
    all_classes = {}
    deps_map = {}

    for entry_point in pkg_resources.iter_entry_points(
            group='hotdoc.extensions', name='get_extension_classes'):
        try:
            activation_function = entry_point.load()
            classes = activation_function()
        # pylint: disable=broad-except
        except Exception as _:
            print "Failed to load %s" % entry_point.module_name, _
            continue

        for klass in classes:
            all_classes[klass.extension_name] = klass

    if not sort:
        return all_classes

    for klass in all_classes.values():
        deps = klass.get_dependencies()
        satisfied = True
        topodeps = set()
        for dep in deps:
            if dep.dependency_name not in all_classes:
                print "Missing dependency %s for %s" % (dep.dependency_name,
                                                        klass.extension_name)
                satisfied = False
                break
            if dep.is_upstream:
                topodeps.add(all_classes[dep.dependency_name])

        if not satisfied:
            continue

        deps_map[klass] = topodeps

    sorted_classes = toposort_flatten(deps_map)
    return sorted_classes

# Recipe from http://code.activestate.com/recipes/576694/


class OrderedSet(collections.MutableSet):
    """
    Banana banana
    """

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, nxt = self.map.pop(key)
            prev[2] = nxt
            nxt[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    # pylint: disable=arguments-differ
    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


def touch(fname):
    """
    Wraps the `touch` command
    """
    subprocess.call(['touch', fname])


def _round8(num):
    return int(math.ceil(num / 8.0)) * 8


class IndentError(HotdocSourceException):
    """
    Banana banana
    """
    pass


def dedent(line):
    """
    Banana banana
    """
    indentation = 0
    for char in line:
        if char not in ' \t':
            break
        indentation += 1
        if char == '\t':
            indentation = _round8(indentation)

    if indentation % 8 != 0:
        raise IndentError(column=indentation)

    return indentation / 8, line.strip()


def dequote(line):
    """
    Banana banana
    """
    if (line[0] == line[-1]) and line.startswith(("'", '"')):
        return line[1:-1]
    return line


def id_from_text(text, add_hash=False):
    """
    Banana banana
    """
    id_ = text.strip().lower().replace(' ', '-').replace(
        '\t', '-').replace('\n', '-')
    # We don't want no utf-8 in urls
    id_ = str(re.sub(r'[^\x00-\x7F]+', '', id_))
    if add_hash:
        id_ = u'#%s' % id_.translate(
            None, r"[!\"#$%&'\(\)\*\+,\.\/:;<=>\?\@\[\\\]\^`\{\|\}~]")
    else:
        id_ = id_.translate(
            None, r"[!\"#$%&'\(\)\*\+,\.\/:;<=>\?\@\[\\\]\^`\{\|\}~]")
    return id_
