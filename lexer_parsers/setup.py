import os

from distutils.core import setup, Extension
from distutils.dep_util import newer_group
from distutils.spawn import spawn
from distutils.command.build_ext import build_ext as _build_ext

scanner_source_dir = os.path.abspath('./')
def src(filename):
    return os.path.join(scanner_source_dir, filename)

subdirectories = [scanner_source_dir]

class build_ext(_build_ext):
    def run_flex(self, extension):
        flex_sources = map(src, extension.depends)
        src_dir = os.path.dirname (extension.depends[0])
        built_scanner_path = src(os.path.join (src_dir, 'scanner.c'))
        extension.sources.append (built_scanner_path)
        if newer_group(flex_sources, built_scanner_path):
            spawn(['flex', '-o', built_scanner_path,
                src(extension.depends[0])],
                  verbose=1)

    def run(self):
        for extension in self.extensions:
            if extension.depends[0].endswith ('.l'):
                self.run_flex (extension)
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

module = Extension('c_comment_scanner',
                    sources = ['c_comment_scanner/scannermodule.c'],
                    depends = ['c_comment_scanner/scanner.l',
                               'c_comment_scanner/scanner.h'])

res = setup (name = 'lexer_parsers',
       version = '1.0',
       description = 'Collection of lexers and parsers',
       cmdclass = {'build_ext': build_ext},
       ext_modules = [module])
