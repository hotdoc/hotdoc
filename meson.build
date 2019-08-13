project(
    'hotdoc',
    'c',
    version : '0.10.0',
    meson_version : '>= 0.51.0',
    license: 'LGPL2+',
)

to_symlink = []
python = import('python').find_installation(get_option('python'))

cmake = import('cmake')
sub_proj = cmake.subproject('cmark')
cmark_dep = sub_proj.dependency('libcmark_static')
cmarkextension_dep = sub_proj.dependency('cmarkextensions_static')

build_system = build_machine.system()
modules = []

env = environment()
cdata = configuration_data()
cdata.set('PYTHON', python.path())
cdata.set('BUILDPATH', meson.current_build_dir())
subdir('hotdoc')
subproject('hotdoc_bootstrap_theme')
theme_dir = meson.current_build_dir() / 'subprojects' / 'hotdoc_bootstrap_theme'

to_symlink += [[theme_dir, meson.current_build_dir() / 'hotdoc' / 'hotdoc_bootstrap_theme']]
install_subdir(theme_dir, install_dir: python.get_install_dir(pure: false) / 'hotdoc')
subdir('documentation')

env.set('PYTHONPATH', meson.current_build_dir())
test(
    'hotdoc tests',
    python,
    args: ['-m', 'unittest', 'discover', '.', '-vvv'],
    env: env,
    workdir: meson.current_source_dir() / 'hotdoc'
)

if meson.version().version_compare('>0.57.5')
    meson.add_devenv(env)
endif

# Used to allow using hotdoc uninstalled
symlink = [python, '-c', '''import sys
import os
sys.path.insert(0, os.path.join(sys.argv[1]))
print('sys.path: %s' % sys.path, file=sys.stderr)
from hotdoc.utils.setup_utils import symlink
symlink(sys.argv[2], sys.argv[3])
''', meson.current_source_dir()]

foreach symlink_info: to_symlink
    res = run_command(symlink, symlink_info[0], symlink_info[1])
    if res.returncode() != 0
        if build_system == 'windows'
            warning('Could not create symlinks:\n @1@\n@0@'.format(res.stdout(), res.stderr()))
        else
            error('Could not create symlinks:\n @1@\n@0@'.format(res.stdout(), res.stderr()))
        endif
    endif
endforeach