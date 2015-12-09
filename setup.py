from setuptools import setup
from distutils.core import Extension
from distutils.errors import DistutilsExecError
from distutils.dep_util import newer_group
from distutils.spawn import spawn
from distutils.command.build_ext import build_ext as _build_ext
from distutils.command.build import build
from distutils.core import Command
from setuptools.command.develop import develop
from setuptools.command.sdist import sdist
from setuptools.command.install import install
import shlex
import shutil
import subprocess
import os, urllib
import tarfile

source_dir = os.path.abspath('./')

class DownloadDefaultTemplate(Command):
    user_options = []
    description = "Download default html template"

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import requests
        response = \
                requests.get('https://people.collabora.com/~meh/hotdoc_bootstrap_theme/dist.tgz')

        with open ('default_theme.tgz', 'wb') as f:
            f.write(response.content)

        tar = tarfile.open('default_theme.tgz')
        extract_path = os.path.join(source_dir, 'hotdoc')
        tar.extractall(extract_path)
        tar.close()

        extract_path = os.path.join(extract_path, 'dist')

        theme_path = os.path.join(source_dir, 'hotdoc', 'default_theme')

        shutil.rmtree(theme_path, ignore_errors=True)

        shutil.move(extract_path, theme_path)

        os.unlink('default_theme.tgz')

class CustomDevelop(develop):
    def run(self):
        self.run_command('download_default_template')
        return develop.run(self)

class CustomBuild(build):
    def run(self):
        self.run_command('download_default_template')
        return build.run(self)

class CustomSDist(sdist):
    def run(self):
        self.run_command('download_default_template')
        return sdist.run(self)

class CustomInstall(install):
    def run(self):
        self.run_command('download_default_template')
        return install.run(self)

source_dir = os.path.abspath('./')
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
      version='0.6.1',
      description='A documentation tool based on clang',
      keywords='documentation gnome clang doxygen',
      url='https://github.com/MathieuDuponchelle/hotdoc',
      author='Mathieu Duponchelle',
      author_email='mathieu.duponchelle@opencreed.com',
      license='LGPL',
      packages=['hotdoc',
                'hotdoc.core',
                'hotdoc.formatters',
                'hotdoc.formatters.html',
                'hotdoc.lexer_parsers',
                'hotdoc.lexer_parsers.doxygen_parser',
                'hotdoc.lexer_parsers.c_comment_scanner',
                'hotdoc.extensions',
                'hotdoc.transition_scripts',
                'hotdoc.utils'],
      cmdclass = {'build_ext': build_ext,
                  'build': CustomBuild,
                  'sdist': CustomSDist,
                  'install': CustomInstall,
                  'develop': CustomDevelop,
                  'download_default_template': DownloadDefaultTemplate},
      ext_modules = [doxygen_block_parser_module, c_comment_scanner_module],
      scripts =
      ['hotdoc/hotdoc'],
      package_data = {
          'hotdoc.formatters.html': ['templates/*', 'assets/*'],
          'hotdoc.extensions': ['templates/*'],
          'hotdoc': ['default_theme/templates/*',
                     'default_theme/js/*',
                     'default_theme/css/*',
                     'default_theme/fonts/*'],
          'hotdoc.transition_scripts': ['translate_sections.sh'],
          },
      install_requires = ['cffi==1.3.0',
                          'wheezy.template==0.1.167',
                          'CommonMark==0.5.4',
                          'lxml==3.4.4',
                          'pygraphviz==1.3.1',
                          'dbus-deviation==0.3.0',
                          'sqlalchemy==1.0.9',
                          'ipython==4.0.0',
                          'pkgconfig==1.1.0',
                          'pygit2==0.22.0'],
      setup_requires = ['requests'],
      zip_safe=False)
