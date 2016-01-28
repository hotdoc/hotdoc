import os
import errno
import shutil
import subprocess
import tarfile
from distutils.command.build import build
from distutils.core import Command

from hotdoc.utils.setup_utils import VersionList
from pkg_resources import parse_version as V
from setuptools import find_packages, setup
from setuptools.command.bdist_egg import bdist_egg
from setuptools.command.develop import develop
from setuptools.command.sdist import sdist

pygit2_version = None
try:
    libgit2_version = subprocess.check_output(['pkg-config', '--modversion',
                                               'libgit2']).strip()
    known_libgit2_versions = VersionList([V('0.22.0'), V('0.23.0')])
    try:
        known_libgit2_version = known_libgit2_versions.find_le(
            V(libgit2_version))

        if known_libgit2_version == V('0.22.0'):
            pygit2_version = '0.22.1'
        elif known_libgit2_version == V('0.23.0'):
            pygit2_version = '0.23.2'
        else:
            print "WARNING: no compatible pygit version found"
            print "git integration disabled"
    except ValueError:
        print "Warning: too old libgit2 version %s" % libgit2_version
        print "git integration disabled"
except OSError as e:
    print "Error when trying to figure out the libgit2 version"
    print "pkg-config is probably not installed\n"
    print "git integration disabled"
except subprocess.CalledProcessError as e:
    print "\nError when trying to figure out the libgit2 version\n"
    print "git integration disabled"

source_dir = os.path.abspath('./')


DEFAULT_THEME =\
        'https://people.collabora.com/~meh/hotdoc_bootstrap_theme/dist.tgz'


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
            requests.get(DEFAULT_THEME)

        with open('default_theme.tgz', 'wb') as f:
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


def symlink(source, link_name):
    import os
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
    user_options = []
    description = "Create links for the style checking pre-commit hooks"

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            symlink(os.path.join(source_dir, 'pre-commit'),
                    os.path.join(source_dir, '.git', 'hooks', 'pre-commit'))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise


class CustomDevelop(develop):

    def run(self):
        self.run_command('download_default_template')
        self.run_command('link_pre_commit_hook')
        return develop.run(self)


class CustomBuild(build):

    def run(self):
        self.run_command('download_default_template')
        return build.run(self)


class CustomSDist(sdist):

    def run(self):
        self.run_command('download_default_template')
        return sdist.run(self)


class CustomBDistEgg(bdist_egg):

    def run(self):
        self.run_command('download_default_template')
        return bdist_egg.run(self)

install_requires = [
    'cffi',
    'git-pylint-commit-hook',
    'git-pep8-commit-hook',
    'wheezy.template==0.1.167',
    'CommonMark==0.6.1',
    'cmarkpy==0.1.3',
    'pygraphviz==1.3.1',
    'sqlalchemy==1.0.9',
    'ipython==4.0.0',
    'toposort==1.4']

if pygit2_version is not None:
    install_requires.append('pygit2==%s' % pygit2_version)

setup(name='hotdoc',
      version='0.6.6',
      description='A documentation tool micro-framework',
      keywords='documentation',
      url='https://github.com/hotdoc/hotdoc',
      author='Mathieu Duponchelle',
      author_email='mathieu.duponchelle@opencreed.com',
      license='LGPL',
      packages=find_packages(),

      # Only fancy thing in there now, we want to download a
      # a default theme and bower is shitty.
      cmdclass={'build': CustomBuild,
                   'sdist': CustomSDist,
                  'develop': CustomDevelop,
                'bdist_egg': CustomBDistEgg,
                'link_pre_commit_hook': LinkPreCommitHook,
                'download_default_template': DownloadDefaultTemplate},
      scripts=['hotdoc/hotdoc'],
      package_data={
          'hotdoc.formatters.html': ['templates/*', 'assets/*'],
          'hotdoc': ['default_theme/templates/*',
                     'default_theme/js/*',
                     'default_theme/css/*',
                     'default_theme/fonts/*'],
      },
      install_requires=install_requires,
      setup_requires=['cffi',
                      'requests'],
      )
