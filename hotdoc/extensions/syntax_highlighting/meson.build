raw_components = run_command(py, ['-c', 'import os; print(" ".join(os.listdir("@0@")))'.format(meson.current_source_dir() / 'prism' / 'components')], check: true).stdout().split(' ')
raw_themes = run_command(py, ['-c', 'import os; print(" ".join(os.listdir("@0@")))'.format(meson.current_source_dir() / 'prism' / 'themes')], check: true).stdout().split(' ')

prism_components = []
foreach component: raw_components
    prism_components += 'prism/components' / component.strip()
endforeach

prism_themes = []
foreach theme: raw_themes
    prism_themes += 'prism/themes' / theme.strip()
endforeach

prism_plugins = [
    'prism/plugins/autoloader/prism-autoloader.js',
    'prism/plugins/keep-markup/prism-keep-markup.js',
]

py.install_sources(
    '__init__.py',
    'prism_autoloader_path_override.js',
    'syntax_extension.py',
    prism_components,
    prism_themes,
    prism_plugins,
    subdir: 'hotdoc/extensions/syntax_highlighting',
    preserve_path: true,
)