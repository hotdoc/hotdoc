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
# pylint: disable=no-name-in-module
from collections import OrderedDict, Callable
import os
import shutil
import math
import sys
import re
import pathlib
import traceback

from urllib.request import urlretrieve

import pkg_resources
from toposort import toposort_flatten

from hotdoc.core.exceptions import HotdocSourceException
from hotdoc.utils.setup_utils import symlink
from hotdoc.utils.loggable import info, debug, error

WIN32 = (sys.platform == 'win32')


if os.name == 'nt':
    DATADIR = os.path.join(os.path.dirname(__file__), '..', 'share')
else:
    DATADIR = "/usr/share"


def splitall(path):
    """
    Splits path in its components:
    foo/bar, /foo/bar and /foo/bar/ will all return
    ['foo', 'bar']
    """
    head, tail = os.path.split(os.path.normpath(path))
    components = []
    while tail:
        components.insert(0, tail)
        head, tail = os.path.split(head)
    return components


def recursive_overwrite(src, dest, ignore=None):
    """
    Banana banana
    """
    if os.path.islink(src):
        linkto = os.readlink(src)
        if os.path.exists(dest):
            os.remove(dest)
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


def flatten_list(list_):
    """
    Banana banana
    """
    res = []

    for elem in list_:
        if isinstance(elem, list):
            res.extend(flatten_list(elem))
        else:
            res.append(elem)

    return res


def get_mtime(filename):
    """
    Banana banana
    """
    try:
        return os.path.getmtime(filename)
    except FileNotFoundError:
        return -1


def __get_extra_extension_classes(paths):
    """
    Banana banana
    """
    extra_classes = []
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
        except Exception as exc:
            info("Failed to load %s %s" % (entry_point.module_name, exc))
            debug(traceback.format_exc())
            continue

        for klass in classes:
            extra_classes.append(klass)

    return extra_classes


# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
def get_extension_classes(sort, extra_extension_paths=None):
    """
    Banana banana
    """
    all_classes = {}
    deps_map = {}

    for entry_point in pkg_resources.iter_entry_points(
            group='hotdoc.extensions', name='get_extension_classes'):
        if entry_point.module_name == 'hotdoc_c_extension.extensions':
            continue
        try:
            activation_function = entry_point.load()
            classes = activation_function()
        # pylint: disable=broad-except
        except Exception as exc:
            info("Failed to load %s" % entry_point.module_name, exc)
            debug(traceback.format_exc())
            continue

        for klass in classes:
            all_classes[klass.extension_name] = klass

    if extra_extension_paths:
        for klass in __get_extra_extension_classes(extra_extension_paths):
            all_classes[klass.extension_name] = klass

    klass_list = list(all_classes.values())
    if not sort:
        return klass_list

    for i, klass in enumerate(klass_list):
        deps = klass.get_dependencies()
        topodeps = set()
        for dep in deps:
            if dep.dependency_name not in all_classes:
                if dep.optional:
                    continue
                else:
                    error("setup-issue",
                          "Missing dependency %s for %s" %
                          (dep.dependency_name, klass.extension_name))
            if dep.is_upstream:
                topodeps.add(
                    klass_list.index(all_classes[dep.dependency_name]))

        deps_map[i] = topodeps

    sorted_class_indices = toposort_flatten(deps_map)
    sorted_classes = [klass_list[i] for i in sorted_class_indices]
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

    # pylint: disable=arguments-differ
    def add(self, key):
        """
        Banana banana
        """
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def __getstate__(self):
        if not self:
            # The state can't be an empty list.
            # We need to return a truthy value, or else
            # __setstate__ won't be run.
            #
            # This could have been done more gracefully by always putting
            # the state in a tuple, but this way is backwards- and forwards-
            # compatible with previous versions of OrderedSet.
            return (None,)
        return list(self)

    def __setstate__(self, state):
        if state == (None,):
            self.__init__([])
        else:
            self.__init__(state)

    # pylint: disable=arguments-differ
    def discard(self, key):
        """
        Banana banana
        """
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
        """
        Banana banana
        """
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
    Mimics the `touch` command

    Busy loops until the mtime has actually been changed, use for tests only
    """
    orig_mtime = get_mtime(fname)
    while get_mtime(fname) == orig_mtime:
        pathlib.Path(fname).touch()


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

    return indentation // 8, line.strip()


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
    id_ = text.strip().lower()

    # No unicode in urls
    id_ = id_.encode('ascii', errors='ignore').decode()

    id_ = re.sub(r"[^\w\s]", '', id_)
    id_ = re.sub(r"\s+", '-', id_)
    if add_hash:
        return '#%s' % id_
    return id_


def get_cat(path):
    """
    Banana banana
    """
    filename, _ = urlretrieve(
        'http://thecatapi.com/api/images/get?format=src&type=gif',
        filename=path)
    return filename


class DefaultOrderedDict(OrderedDict):
    """
    Banana banana
    """
    # Source: http://stackoverflow.com/a/6190500/562769
    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
                not isinstance(default_factory, Callable)):
            raise TypeError('first argument must be callable')
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = (self.default_factory,)
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                               OrderedDict.__repr__(self))
