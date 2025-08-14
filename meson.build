# SPDX-FileCopyrightText: Corentin Noël <corentin.noel@collabora.com>
# SPDX-License-Identifier: LGPL-2.1-or-later

project(
  'hotdoc', 'c',
  license: 'LGPL-2.1-or-later',
  meson_version: '>= 1.0.0',
  default_options: [
    'buildtype=release',
    'c_std=c11',
  ]
)

cmake = import('cmake')

py = import('python').find_installation(pure: false)

subdir('hotdoc')

test_dir_env = environment({'TEST_BASE_THEME_DIR': theme_dist_dir})
test(
  'unittest',
  py,
  args: ['-m', 'unittest'],
  workdir: meson.current_source_dir(),
  env: test_dir_env,
)