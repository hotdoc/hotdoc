from setuptools import setup
from distutils.core import Extension
from distutils.errors import DistutilsExecError
from distutils.dep_util import newer_group
from distutils.spawn import spawn
from distutils.command.build_ext import build_ext as _build_ext
import shlex
import subprocess
import os

source_dir = os.path.abspath('./')
print "source dir is ", source_dir
def src(filename):
    return os.path.join(source_dir, filename)

def PkgConfig(package, args):
    pcfg = None
    try:
        subprocess.check_call(['pkg-config', '--exists', package])
        cmd = ['pkg-config', package]
        for arg in args:
            cmd.append (arg)
        pcfg = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError as osexception:
        if osexception.errno == errno.ENOENT:
            raise DistutilsExecError,\
                    ('pkg-config not found')
        else:
            raise DistutilsExecError,\
                    ("Running pkg-config failed - %s." % osexception)
    except subprocess.CalledProcessError:
        raise DistutilsExecError,\
                ("Did not find %s via pkg-config." % package)

    if pcfg is not None:
        output, _ = pcfg.communicate()
        res = output.split(" ")
        return filter(lambda a: a not in [' ', '\n'], res)

def check_pkgconfig():
    """ pull compile / link flags from pkg-config if present. """
    pcfg = None
    try:
        check_call(['pkg-config', '--exists', 'libzmq'])
        # this would arguably be better with --variable=libdir /
        # --variable=includedir, but would require multiple calls
        pcfg = Popen(['pkg-config', '--libs', '--cflags', 'libzmq'],
                     stdout=subprocess.PIPE)
    except OSError as osexception:
        if osexception.errno == errno.ENOENT:
            info('pkg-config not found')
        else:
            warn("Running pkg-config failed - %s." % osexception)
    except CalledProcessError:
        info("Did not find libzmq via pkg-config.")

    if pcfg is not None:
        output, _ = pcfg.communicate()
        output = output.decode('utf8', 'replace')
        bits = output.strip().split()
        zmq_config = {'library_dirs':[], 'include_dirs':[], 'libraries':[]}
        for tok in bits:
            if tok.startswith("-L"):
                zmq_config['library_dirs'].append(tok[2:])
            if tok.startswith("-I"):
                zmq_config['include_dirs'].append(tok[2:])
            if tok.startswith("-l"):
                zmq_config['libraries'].append(tok[2:])
        info("Settings obtained from pkg-config: %r" % zmq_config)

    return zmq_config



class build_ext(_build_ext):
    def run(self):
        for extension in self.extensions:
            if hasattr (extension, 'build_custom'):
                extension.build_custom ()

        _build_ext.run(self)
        return True


class FlexBisonExtension (Extension):
    def __init__(self, flex_sources, bison_sources, *args, **kwargs):
        Extension.__init__(self, *args, **kwargs)
        self.__flex_sources = [src(s) for s in flex_sources]
        self.__bison_sources = [src(s) for s in bison_sources]

    def __build_flex(self):
        src_dir = os.path.dirname (self.__flex_sources[0])
        built_scanner_path = src(os.path.join (src_dir, 'scanner.c'))
        self.sources.append (built_scanner_path)

        if newer_group(self.__flex_sources, built_scanner_path):
            cmd = ['flex', '-o', built_scanner_path]
            for s in self.__flex_sources:
                cmd.append (s)
            print "flex cmd baby", cmd
            try:
                spawn(cmd, verbose=1)
            except DistutilsExecError:
                raise DistutilsExecError,\
                        ("Make sure flex is installed on your system")

    def __build_bison(self):
        src_dir = os.path.dirname (self.__bison_sources[0])
        built_parser_path = src(os.path.join (src_dir, 'parser.c'))
        print 'parser_path : ', built_parser_path
        self.sources.append (built_parser_path)

        if newer_group(self.__bison_sources, built_parser_path):
            cmd = ['bison', '-o', built_parser_path]
            for s in self.__bison_sources:
                cmd.append (s)
            print "biosn cmd baby", cmd
            try:
                spawn(cmd, verbose=1)
            except DistutilsExecError:
                raise DistutilsExecError,\
                        ("Make sure bison is installed on your system")

    def build_custom (self):
        if self.__flex_sources:
            self.__build_flex()
        if self.__bison_sources:
            self.__build_bison()

try:
    ghc_version = subprocess.check_output(['ghc', "--numeric-version"]).strip()
except:
    raise DistutilsExecError,\
            ("Make sure you have a haskell compiler named ghc")

class HaskellExtension (Extension):
    def __init__(self, haskell_sources, *args, **kwargs):
        Extension.__init__(self, *args, **kwargs)
        self.__haskell_sources = [src(s) for s in haskell_sources]

    def build_custom (self):
        src_dir = os.path.dirname (self.__haskell_sources[0])
        bindings_lib = src (os.path.join (src_dir, "libConvert.so"))
        cmd = ['ghc', '-O2', '-dynamic', '-shared', '-fPIC',
                    '-o', bindings_lib, '-lHSrts-ghc%s' % str (ghc_version)]
        for s in self.__haskell_sources:
            cmd.append (s)
        try:
            spawn (cmd, verbose=1)
        except DistutilsExecError:
            raise DistutilsExecError,\
                    ("Compiling the python bindings for pandoc failed, make"
                     "sure you have a haskell compiler named ghc, and that"
                     "the pandoc development package is installed")


glib_cflags = [flag for flag in PkgConfig ('glib-2.0', ['--cflags']) if flag]
glib_libs = [flag for flag in PkgConfig ('glib-2.0', ['--libs']) if flag]

doxygen_block_parser_module = FlexBisonExtension(
                                ['better_doc_tool/lexer_parsers/doxygen_parser/doxenizer.l'],
                                [],
                                'better_doc_tool.lexer_parsers.doxygen_parser.doxygen_parser',
                                sources =
                                ['better_doc_tool/lexer_parsers/doxygen_parser/doxparser_module.c',
                                 'better_doc_tool/lexer_parsers/doxygen_parser/doxparser.c'],
                                depends =
                                ['better_doc_tool/lexer_parsers/doxygen_parser/doxenizer.h',
                                 'better_doc_tool/lexer_parsers/doxygen_parser/doxparser.h',
                                 'better_doc_tool/lexer_parsers/doxygen_parser/doxenizer.l'],
                                extra_compile_args = glib_cflags,
                                extra_link_args = glib_libs)

gtk_doc_parser_module = FlexBisonExtension(
                                ['better_doc_tool/lexer_parsers/gtkdoc_parser/lexer.l'],
                                ['better_doc_tool/lexer_parsers/gtkdoc_parser/parser.y'],
                                'better_doc_tool.lexer_parsers.gtkdoc_parser.gtkdoc_parser',
                                sources =
                                ['better_doc_tool/lexer_parsers/gtkdoc_parser/gtkdoc_parser_module.c',
                                 'better_doc_tool/lexer_parsers/gtkdoc_parser/comment_module_interface.c'],
                                depends =
                                ['better_doc_tool/lexer_parsers/gtkdoc_parser/comment_module_interface.h',
                                 'better_doc_tool/lexer_parsers/gtkdoc_parser/lexer.l',
                                 'better_doc_tool/lexer_parsers/gtkdoc_parser/parser.y'])

pandoc_translator_module = HaskellExtension(
        ['better_doc_tool/core/pandoc_interface/translator.hs',
        'better_doc_tool/core/pandoc_interface/doc_translator.c'],
        'better_doc_tool.core.pandoc_interface.translator',
        sources = ['better_doc_tool/core/pandoc_interface/translator_module.c'],
        depends=
            ['better_doc_tool/core/pandoc_interface/translator.hs',
            'better_doc_tool/core/pandoc_interface/doc_translator.c'])

setup(name='better_doc_tool',
      version='0.2',
      description='A documentation tool based on pandoc',
      keywords='documentation gnome pandoc doxygen',
      url='https://github.com/MathieuDuponchelle/better_doctool',
      author='Mathieu Duponchelle',
      author_email='mathieu.duponchelle@opencreed.com',
      license='LGPL',
      packages=['better_doc_tool',
                'better_doc_tool.core',
                'better_doc_tool.core.pandoc_interface',
                'better_doc_tool.clang_interface',
                'better_doc_tool.formatters',
                'better_doc_tool.lexer_parsers',
                'better_doc_tool.lexer_parsers.gtkdoc_parser',
                'better_doc_tool.lexer_parsers.doxygen_parser',
                'better_doc_tool.extensions',
                'better_doc_tool.utils'],
      cmdclass = {'build_ext': build_ext},
      ext_modules = [doxygen_block_parser_module, gtk_doc_parser_module,
          pandoc_translator_module],
      scripts = ['bdt.py'],
      package_data = {
          'better_doc_tool.core.pandoc_interface': ['libConvert.*'],
          'better_doc_tool.formatters': ['templates/*', 'style.css'],
          },
      install_requires = ['wheezy.template',
                          'pandocfilters',
                          'clang',
                          'lxml'],
      zip_safe=False)
