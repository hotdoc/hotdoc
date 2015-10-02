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
            build_path = None
            for output in self.get_outputs():
                name = os.path.splitext(os.path.basename (output))[0]
                if extension.name.endswith(name):
                    build_path = os.path.dirname(output)

            if hasattr (extension, 'build_custom'):
                extension.build_custom (build_path)

        _build_ext.run(self)
        return True


class FlexExtension (Extension):
    def __init__(self, flex_sources, *args, **kwargs):
        Extension.__init__(self, *args, **kwargs)
        self.__flex_sources = [src(s) for s in flex_sources]

    def __build_flex(self):
        src_dir = os.path.dirname (self.__flex_sources[0])
        built_scanner_path = src(os.path.join (src_dir, 'scanner.c'))
        self.sources.append (built_scanner_path)

        if newer_group(self.__flex_sources, built_scanner_path):
            cmd = ['flex', '-o', built_scanner_path]
            for s in self.__flex_sources:
                cmd.append (s)
            try:
                spawn(cmd, verbose=1)
            except DistutilsExecError:
                raise DistutilsExecError,\
                        ("Make sure flex is installed on your system")

    def build_custom (self, build_path):
        if self.__flex_sources:
            self.__build_flex()

glib_cflags = [flag for flag in PkgConfig ('glib-2.0', ['--cflags']) if flag]
glib_libs = [flag for flag in PkgConfig ('glib-2.0', ['--libs']) if flag]

doxygen_block_parser_module = FlexExtension(
                                ['hotdoc/lexer_parsers/doxygen_parser/doxenizer.l'],
                                'hotdoc.lexer_parsers.doxygen_parser.doxygen_parser',
                                sources =
                                ['hotdoc/lexer_parsers/doxygen_parser/doxparser_module.c',
                                 'hotdoc/lexer_parsers/doxygen_parser/doxparser.c'],
                                depends =
                                ['hotdoc/lexer_parsers/doxygen_parser/doxenizer.h',
                                 'hotdoc/lexer_parsers/doxygen_parser/doxparser.h',
                                 'hotdoc/lexer_parsers/doxygen_parser/doxenizer.l'],
                                extra_compile_args = glib_cflags,
                                extra_link_args = glib_libs)

c_comment_scanner_module = FlexExtension(
                            ['hotdoc/lexer_parsers/c_comment_scanner/scanner.l'],
                            'hotdoc.lexer_parsers.c_comment_scanner.c_comment_scanner',
                            sources =
                            ['hotdoc/lexer_parsers/c_comment_scanner/scannermodule.c'],
                            depends =
                            ['hotdoc/lexer_parsers/c_comment_scanner/scanner.l',
                            'hotdoc/lexer_parsers/c_comment_scanner/scanner.h'])

setup(name='hotdoc',
      version='0.4.9',
      description='A documentation tool based on clang',
      keywords='documentation gnome clang doxygen',
      url='https://github.com/MathieuDuponchelle/hotdoc',
      author='Mathieu Duponchelle',
      author_email='mathieu.duponchelle@opencreed.com',
      license='LGPL',
      packages=['hotdoc',
                'hotdoc.core',
                'hotdoc.clang_interface',
                'hotdoc.formatters',
                'hotdoc.formatters.html',
                'hotdoc.lexer_parsers',
                'hotdoc.lexer_parsers.doxygen_parser',
                'hotdoc.lexer_parsers.c_comment_scanner',
                'hotdoc.extensions',
                'hotdoc.utils'],
      cmdclass = {'build_ext': build_ext},
      ext_modules = [doxygen_block_parser_module, c_comment_scanner_module],
      scripts =
      ['hotdoc/hotdoc',
       'hotdoc/transition_scripts/sgml_to_sections.py',
       'hotdoc/transition_scripts/translate_sections.sh'],
      package_data = {
          'hotdoc.formatters.html': ['templates/*', 'style.css',
              'redstyle.css', 'greenstyle.css', 'home.png', 'API_index.js'],
          'hotdoc.extensions': ['templates/*'],
          },
      install_requires = ['wheezy.template',
                          'CommonMark',
                          'lxml',
                          'pygraphviz',
                          'dbus-deviation'],
      zip_safe=False)
