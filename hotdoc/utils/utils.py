import shlex
import pkgutil, importlib, sys, os
import subprocess
import traceback
from pkg_resources import iter_entry_points

def PkgConfig(args):
    cmd = ['pkg-config'] + shlex.split(args)
    out = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE).stdout
    line = out.readline()[:-1].split(" ")
    return filter(lambda a: a not in [' ', ''], line)

def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in all_subclasses(s)]

def get_extension_classes():
    all_classes = {}

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

    print all_classes
