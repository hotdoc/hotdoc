"""
Banana banana
"""
import collections
import os
import shutil
import sys

from pkg_resources import iter_entry_points
from toposort import toposort_flatten

WIN32 = (sys.platform == 'win32')


def recursive_overwrite(src, dest, ignore=None):
    """
    Banana banana
    """
    if os.path.isdir(src):
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


def get_all_extension_classes(sort):
    """
    Banana banana
    """
    all_classes = {}
    deps_map = {}

    for entry_point in iter_entry_points(group='hotdoc.extensions',
                                         name='get_extension_classes'):
        try:
            activation_function = entry_point.load()
            classes = activation_function()
        # pylint: disable=broad-except
        except Exception as _:
            print "Failed to load %s" % entry_point.module_name, _
            continue

        for klass in classes:
            all_classes[klass.EXTENSION_NAME] = klass

    if not sort:
        return all_classes

    for klass in all_classes.values():
        deps = klass.get_dependencies()
        satisfied = True
        topodeps = set()
        for dep in deps:
            if dep.dependency_name not in all_classes:
                print "Missing dependency %s for %s" % (dep.dependency_name,
                                                        klass.EXTENSION_NAME)
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
