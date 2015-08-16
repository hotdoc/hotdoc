import shlex
import subprocess

def PkgConfig(args):
    cmd = ['pkg-config'] + shlex.split(args)
    out = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE).stdout
    line = out.readline()[:-1].split(" ")
    return filter(lambda a: a != ' ', line)

def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in all_subclasses(s)]
