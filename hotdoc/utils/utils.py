import shlex
import pkgutil, importlib, sys, os
import subprocess
import traceback
from pkg_resources import iter_entry_points
from toposort import toposort_flatten
import collections

def PkgConfig(args):
    cmd = ['pkg-config'] + shlex.split(args)
    out = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE).stdout
    line = out.readline()[:-1].split(" ")
    return filter(lambda a: a not in [' ', ''], line)

def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in all_subclasses(s)]

def get_all_extension_classes(sort):
    all_classes = {}
    deps_map = {}

    for entry_point in iter_entry_points(group='hotdoc.extensions',
            name='get_extension_classes'):
        entry_point.module_name
        try:
            activation_function = entry_point.load()
            classes = activation_function()
        except Exception as e:
            print "Failed to load %s" % entry_point.module_name, e
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
            if dep.upstream == True:
                topodeps.add(all_classes[dep.dependency_name])

        if not satisfied:
            continue

        deps_map[klass] = topodeps


    sorted_classes = toposort_flatten(deps_map)
    return sorted_classes

# Recipe from http://code.activestate.com/recipes/576694/
class OrderedSet(collections.MutableSet):

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
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

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
