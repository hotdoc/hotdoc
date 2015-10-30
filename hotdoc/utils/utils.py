import re, os
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


def __find_included_file(filename, include_paths):
    if os.path.isabs(filename):
        return filename

    for include_path in include_paths:
        fpath = os.path.join(include_path, filename)
        if os.path.exists(fpath):
            return fpath

    return filename


def markdown_include_content(contents, source_file, include_paths, lineno=0):
    inclusions = re.findall("\n *{{.*}} *\n", contents)
    for inclusion in inclusions:
        include_path = __find_included_file(re.sub("\n|{{|}}| ", "", inclusion),
                                            include_paths)
        try:
            included_content = open(include_path, 'r').read()
            nincluded_content = included_content
            including = True
            while including:
                nincluded_content = markdown_include_content(
                    nincluded_content, include_path, include_paths, lineno)
                including = (nincluded_content != included_content)
                included_content = nincluded_content
        except Exception as e:
            raise type(e)("Could not include %s in %s - include line: '%s'"
                          " (%s)" % (include_path, source_file,
                                     lineno, e.message))

        contents = contents.replace(inclusion, included_content)

    return contents
