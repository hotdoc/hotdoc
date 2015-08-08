import os

from distutils.core import setup, Extension
from distutils.dep_util import newer_group
from distutils.spawn import spawn
from distutils.command.build_ext import build_ext as _build_ext
from fnmatch import fnmatch
import shlex
import subprocess

def PkgConfig(args):
    cmd = ['pkg-config'] + shlex.split(args)
    out = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE).stdout
    line = out.readline()[:-1].split(" ")
    return filter(lambda a: a != ' ', line)

scanner_source_dir = os.path.abspath('./')
def src(filename):
    return os.path.join(scanner_source_dir, filename)

def is_bison_source (filename):
    return any (fnmatch  (filename, p) for p in ('*.h', '*.y'))

def is_flex_source (filename):
    return any (fnmatch  (filename, p) for p in ('*.h', '*.l'))

class build_ext(_build_ext):
    def run_flex(self, extension):
        depends = [src (d) for d in extension.depends]
        flex_sources = [s for s in depends if is_flex_source (s)]
        src_dir = os.path.dirname (extension.depends[0])
        built_scanner_path = src(os.path.join (src_dir, 'scanner.c'))
        extension.sources.append (built_scanner_path)
        if newer_group(flex_sources, built_scanner_path):
            spawn(['flex', '-o', built_scanner_path,
                src(extension.depends[0])],
                  verbose=1)

    def run_bison (self, extension):
        depends = [src (d) for d in extension.depends]
        bison_sources = [s for s in depends if is_bison_source (s)]
        print bison_sources
        src_dir = os.path.dirname (extension.depends[0])
        built_parser_path = src(os.path.join (src_dir, 'parser.c'))
        extension.sources.append (built_parser_path)
        if newer_group(bison_sources, built_parser_path):
            spawn(['bison', '-o', built_parser_path,
                src(extension.depends[1])],
                  verbose=1)

    def run(self):
        for extension in self.extensions:
            if extension.depends[0].endswith ('.l'):
                self.run_flex (extension)
            if extension.depends[1].endswith ('.y'):
                self.run_bison (extension)

        _build_ext.run(self)

        for extension in self.extensions:
            for output in self.get_outputs():
                output_basename = os.path.basename (os.path.splitext(output)[0])
                if output_basename == extension.name:
                    src_dir = src(os.path.dirname (extension.sources[0]))
                    dest = src(os.path.join(src_dir, os.path.basename (output)))
                    if hasattr (os, 'symlink'):
                        try:
                            os.unlink (dest)
                        except OSError:
                            pass

                        self.copy_file (src(output), dest, link='sym')
                    else:
                        self.copy_file (src(output), dest)
                    break

glib_cflags = [flag for flag in PkgConfig ('--cflags glib-2.0') if flag]
glib_libs = [flag for flag in PkgConfig ('--libs glib-2.0') if flag]

doxygen_block_parser_module = Extension('doxygen_parser',
                                sources = ['doxygen_parser/doxparser_module.c',
                                           'doxygen_parser/doxparser.c'],
                                depends = ['doxygen_parser/doxenizer.l',
                                           'doxygen_parser/doxenizer.h',
                                           'doxygen_parser/doxparser.h'],
                                extra_compile_args = glib_cflags,
                                extra_link_args = glib_libs)

gtk_doc_parser_module = Extension('gtkdoc_parser',
                                sources =
                                ['gtkdoc_parser/gtkdoc_parser_module.c',
                                 'gtkdoc_parser/comment_module_interface.c'],
                                depends = ['gtkdoc_parser/lexer.l',
                                           'gtkdoc_parser/parser.y',
                                           'gtkdoc_parser/comment_module_interface.h'])

res = setup (name = 'lexer_parsers',
       version = '1.0',
       description = 'Collection of lexers and parsers',
       cmdclass = {'build_ext': build_ext},
       ext_modules = [doxygen_block_parser_module,
                      gtk_doc_parser_module])
