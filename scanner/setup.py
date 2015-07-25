import os

from distutils.core import setup, Extension
from distutils.dep_util import newer_group
from distutils.spawn import spawn
from distutils.command.build_ext import build_ext as _build_ext
from distutils.command.clean import clean as _clean

scanner_source_dir = os.path.abspath('./')
def src(filename):
    return os.path.join(scanner_source_dir, filename)

class build_ext(_build_ext):
    def run_flex(self):
        flex_dependencies = ['scanner.h',
                             'scanner.l']
        flex_sources = map(src, flex_dependencies)
        if newer_group(flex_sources, src('scanner.c')):
            spawn(['flex', '-o', src('scanner.c'), src('scanner.l')],
                  verbose=1)

    def run(self):
        self.run_flex()
        _build_ext.run(self)

class clean (_clean):
    def clean_flex (self):
        try:
            os.unlink ('scanner.c')
        except OSError:
            pass
        try:
            os.unlink ('scanner.so')
        except OSError:
            pass

    def run(self):
        self.clean_flex ()
        _clean.run(self)

module = Extension('scanner',
                    sources = ['scannermodule.c', 'scanner.c'])

res = setup (name = 'Scanner',
       version = '1.0',
       description = 'This is simple C source code scanner',
       cmdclass = {'build_ext': build_ext,
                   'clean': clean},
       ext_modules = [module])
