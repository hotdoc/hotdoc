import shlex
import pkgutil, importlib, sys, os
import subprocess
import traceback

def PkgConfig(args):
    cmd = ['pkg-config'] + shlex.split(args)
    out = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE).stdout
    line = out.readline()[:-1].split(" ")
    return filter(lambda a: a not in [' ', ''], line)

def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in all_subclasses(s)]

def load_extensions(dirname):
    package = importlib.import_module(dirname)
    prefix = package.__name__ + '.'
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__,
            prefix):
        if modname in sys.modules:
            continue
        try:
            module = importlib.import_module(modname)
        except Exception as e:
            print "Extension %s disabled : %s" % (modname, e)
            if os.environ.get('DOC_DEBUG'):
                traceback.print_exc()


def load_all_extensions():
    extension_paths = os.environ.get('HOTDOC_EXTENSION_PATH')
    if extension_paths:
        extension_paths = extension_paths.split(':')
    else:
        extension_paths = []

    extension_paths.append('hotdoc.extensions')
    for path in extension_paths:
        load_extensions(path)
