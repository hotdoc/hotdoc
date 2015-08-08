import os

from distutils.core import setup, Extension
from distutils.dep_util import newer_group
from distutils.spawn import spawn
from distutils.command.build_ext import build_ext as _build_ext
import subprocess

ghc_version = subprocess.check_output(['ghc', "--numeric-version"]).strip()

source_dir = os.path.abspath('./')
def src(filename):
    return os.path.join(source_dir, filename)

class build_ext (_build_ext):
    def make_haskell_binding (self, extension):
        depends =  [src (d) for d in extension.depends]
        src_dir = os.path.dirname (extension.depends[0])
        bindings_lib = src (os.path.join (src_dir, "libConvert.so"))
        cmd = ['ghc', '-O2', '-dynamic', '-shared', '-fPIC',
                    '-o', bindings_lib, '-lHSrts-ghc%s' % str (ghc_version)]
        for d in depends:
            cmd.append (d)
        if newer_group (depends, bindings_lib):
            spawn (cmd, verbose=1)

    def copy_or_link_module (self):
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

    def run (self):
        for extension in self.extensions:
            self.make_haskell_binding (extension)
        _build_ext.run (self)
        self.copy_or_link_module ()

translator_module = Extension('translator',
                            sources = ['pandoc_interface/translator_module.c'],
                            depends = ['pandoc_interface/translator.hs',
                                       'pandoc_interface/doc_translator.c'])

res = setup (name = 'translator',
       version = '1.0',
       description = 'Pandoc translator through funny bindings',
       cmdclass = {'build_ext': build_ext},
       ext_modules = [translator_module])
