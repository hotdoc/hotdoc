# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""
Setup file for hotdoc.
"""

import os
import sys
import errno
import shutil
import tarfile
import unittest
from distutils.command.build import build
from distutils.command.build_ext import build_ext
from distutils.core import Command
import distutils.spawn as spawn

from setuptools import find_packages, setup, Extension
from setuptools.command.bdist_egg import bdist_egg
from setuptools.command.develop import develop
from setuptools.command.sdist import sdist
from setuptools.command.test import test

from hotdoc.utils.setup_utils import (
    VERSION, THEME_VERSION, require_clean_submodules)

SOURCE_DIR = os.path.abspath('./')
CMARK_DIR = os.path.join(SOURCE_DIR, 'cmark')
CMARK_SRCDIR = os.path.join(CMARK_DIR, 'src')
CMARK_EXTDIR = os.path.join(CMARK_DIR, 'extensions')
CMARK_BUILD_DIR = os.path.join(SOURCE_DIR, 'build_cmark')
CMARK_BUILT_SRCDIR = os.path.join(CMARK_BUILD_DIR, 'src')
CMARK_INCLUDE_DIRS = [CMARK_SRCDIR, CMARK_BUILT_SRCDIR]

require_clean_submodules(SOURCE_DIR, ['cmark'])


# pylint: disable=too-few-public-methods
class CMarkExtension(Extension):
    """
    A custom extension that will run cmake in the cmark subdir
    before building itself.
    """
    # pylint: disable=no-self-use
    def __run_cmake(self):
        if spawn.find_executable('cmake') is None:
            print "cmake  is required"
            print "Please install cmake and re-run setup"
            sys.exit(-1)
        if spawn.find_executable('make') is None:
            print "make  is required"
            print "please get a version of make and re-run setup"
            sys.exit(-1)

        cwd = os.getcwd()
        if not os.path.exists(CMARK_BUILD_DIR):
            os.mkdir(CMARK_BUILD_DIR)
        os.chdir(CMARK_BUILD_DIR)
        try:
            spawn.spawn(['cmake', CMARK_DIR])
            spawn.spawn(['make', 'cmarkextensions'])
        except spawn.DistutilsExecError:
            print "Error while running cmake"
            sys.exit(-1)
        os.chdir(cwd)

    # pylint: disable=missing-docstring
    def build_custom(self):
        self.__run_cmake()

CMARK_SOURCES = [os.path.join('hotdoc', 'parsers', f) for f in
                 ('cmark_module.c',
                  'cmark_gtkdoc_extension.c',
                  'cmark_gtkdoc_scanner.c',
                  'cmark_include_extension.c',
                  'cmark_include_scanner.c',)]

for filename in os.listdir(CMARK_SRCDIR):
    if filename.endswith('.c'):
        CMARK_SOURCES.append(os.path.join(CMARK_SRCDIR, filename))

for filename in os.listdir(CMARK_EXTDIR):
    if filename.endswith('.c'):
        CMARK_SOURCES.append(os.path.join(CMARK_EXTDIR, filename))

CMARK_MODULE = CMarkExtension('hotdoc.parsers.cmark',
                              sources=CMARK_SOURCES,
                              include_dirs=CMARK_INCLUDE_DIRS,
                              define_macros=[
                                  ('LIBDIR', '"%s"' % CMARK_BUILD_DIR)])


DEFAULT_THEME =\
    'https://people.collabora.com/~meh/hotdoc_bootstrap_theme-%s/dist.tgz' % \
    THEME_VERSION


class DownloadDefaultTemplate(Command):
    """
    This will download the default theme (bootstrap)
    """
    user_options = []
    description = "Download default html template"

    # pylint: disable=missing-docstring
    def initialize_options(self):
        pass

    # pylint: disable=missing-docstring
    def finalize_options(self):
        pass

    # pylint: disable=missing-docstring
    # pylint: disable=no-self-use
    def run(self):
        theme_path = os.path.join(SOURCE_DIR, 'hotdoc', 'default_theme-%s' %
                                  THEME_VERSION)

        if os.path.exists(theme_path):
            return

        # Only installed at setup_requires time, whatever
        # pylint: disable=import-error
        import requests
        response = \
            requests.get(DEFAULT_THEME)

        with open('default_theme.tgz', 'wb') as _:
            _.write(response.content)

        tar = tarfile.open('default_theme.tgz')
        extract_path = os.path.join(SOURCE_DIR, 'hotdoc')
        tar.extractall(extract_path)
        tar.close()

        extract_path = os.path.join(extract_path, 'dist')

        shutil.rmtree(theme_path, ignore_errors=True)

        shutil.move(extract_path, theme_path)

        os.unlink('default_theme.tgz')


def symlink(source, link_name):
    """
    Method to allow creating symlinks on Windows
    """
    os_symlink = getattr(os, "symlink", None)
    if callable(os_symlink):
        os_symlink(source, link_name)
    else:
        import ctypes
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        flags = 1 if os.path.isdir(source) else 0
        if csl(link_name, source, flags) == 0:
            raise ctypes.WinError()


class LinkPreCommitHook(Command):
    """
    This will create links to the pre-commit hook.
    Only called in develop mode.
    """
    user_options = []
    description = "Create links for the style checking pre-commit hooks"

    # pylint: disable=missing-docstring
    def initialize_options(self):
        pass

    # pylint: disable=missing-docstring
    def finalize_options(self):
        pass

    # pylint: disable=missing-docstring
    # pylint: disable=no-self-use
    def run(self):
        try:
            symlink(os.path.join(SOURCE_DIR, 'pre-commit'),
                    os.path.join(SOURCE_DIR, '.git', 'hooks', 'pre-commit'))
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise


# pylint: disable=missing-docstring
# pylint: disable=too-few-public-methods
class CustomDevelop(develop):

    def run(self):
        self.run_command('download_default_template')
        self.run_command('link_pre_commit_hook')
        return develop.run(self)


# pylint: disable=missing-docstring
class CustomBuild(build):

    def run(self):
        self.run_command('download_default_template')
        return build.run(self)


# pylint: disable=missing-docstring
class CustomSDist(sdist):

    def run(self):
        self.run_command('download_default_template')
        return sdist.run(self)


# pylint: disable=missing-docstring
class CustomBDistEgg(bdist_egg):

    def run(self):
        self.run_command('download_default_template')
        return bdist_egg.run(self)


class CustomBuildExt(build_ext):
    def run(self):
        for extension in self.extensions:
            extension.build_custom()

        build_ext.run(self)
        return True


# From http://stackoverflow.com/a/17004263/2931197
def discover_and_run_tests(forever):
    # use the default shared TestLoader instance
    test_loader = unittest.defaultTestLoader

    # use the basic test runner that outputs to sys.stderr
    test_runner = unittest.TextTestRunner()

    # automatically discover all tests
    # NOTE: only works for python 2.7 and later
    test_suite = test_loader.discover(SOURCE_DIR)

    # run the test suite
    loop = True
    while loop:
        res = test_runner.run(test_suite)
        if res.errors or res.failures or not forever:
            loop = False


class DiscoverTest(test):
    user_options = test.user_options + [('forever', None, 'Run until failure')]

    def __init__(self, *args, **kwargs):
        test.__init__(self, *args, **kwargs)
        self.test_args = []
        self.test_suite = True
        self.forever = False

    def initialize_options(self):
        test.initialize_options(self)
        self.forever = False

    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        discover_and_run_tests(self.forever)


INSTALL_REQUIRES = [
    'pyyaml',
    'lxml',
    'schema',
    'wheezy.template==0.1.167',
    'pygraphviz>=1.3.rc2',
    'sqlalchemy>=1.0.8',
    'toposort==1.4']

EXTRAS_REQUIRE = {
    'dev': ['git-pylint-commit-hook',
            'git-pep8-commit-hook']
}

# Extensions

SYN_EXT_DIR = os.path.join(SOURCE_DIR, 'hotdoc', 'extensions', 'syntax_highlighting')
require_clean_submodules(SYN_EXT_DIR, ['prism'])

setup(name='hotdoc',
      version=VERSION,
      description='A documentation tool micro-framework',
      keywords='documentation',
      url='https://github.com/hotdoc/hotdoc',
      author='Mathieu Duponchelle',
      author_email='mathieu.duponchelle@opencreed.com',
      license='LGPLv2.1+',
      packages=find_packages(),
      ext_modules=[CMARK_MODULE],

      cmdclass={'build': CustomBuild,
                'build_ext': CustomBuildExt,
                'sdist': CustomSDist,
                'develop': CustomDevelop,
                'bdist_egg': CustomBDistEgg,
                'test': DiscoverTest,
                'link_pre_commit_hook': LinkPreCommitHook,
                'download_default_template': DownloadDefaultTemplate},
      scripts=['hotdoc/hotdoc',
               'hotdoc/hotdoc_dep_printer'],
      package_data={
          'hotdoc.formatters': ['html_templates/*', 'html_assets/*'],
          'hotdoc': ['default_theme-%s/templates/*' % THEME_VERSION,
                     'default_theme-%s/js/*' % THEME_VERSION,
                     'default_theme-%s/css/*' % THEME_VERSION,
                     'default_theme-%s/fonts/*' % THEME_VERSION,
                     'VERSION.txt'],
          'hotdoc.utils': ['hotdoc.m4', 'hotdoc.mk'],
          'hotdoc.extensions.syntax_highlighting': [
              'prism/*',
              'prism/components/*',
              'prism/themes/*',
              'prism/plugins/autoloader/*',
              'prism_autoloader_path_override.js'],
          'hotdoc.extensions.search': [
              '*.js',
              'stopwords.txt'],
          'hotdoc.extensions.devhelp': [
              'devhelp.css'],
          'hotdoc.extensions.license': [
              'data/*',
              'html_templates/*']
      },
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE,
      entry_points={
          'hotdoc.extensions': ('get_extension_classes = '
                                'hotdoc.extensions:get_extension_classes')},
      setup_requires=['requests'])
