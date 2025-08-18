py.install_sources(
    'hotdoc_dep_printer.py',
    'run_hotdoc.py',
    '__init__.py',
    'VERSION.txt',
    'extensions/__init__.py',
    'utils/configurable.py',
    'utils/hotdoc.m4',
    'utils/hotdoc.mk',
    'utils/__init__.py',
    'utils/loggable.py',
    'utils/setup_utils.py',
    'utils/signals.py',
    'utils/utils.py',
    'utils/tests/__init__.py',
    'utils/tests/test_loggable.py',
    'parsers/cmark_utils.py',
    'parsers/gtk_doc.py',
    'parsers/__init__.py',
    'parsers/sitemap.py',
    'parsers/tests/__init__.py',
    'parsers/tests/test_cmark_parser.py',
    'parsers/tests/test_standalone_parser.py',
    'parsers/c_comment_scanner/__init__.py',
    subdir: 'hotdoc',
    preserve_path: true,
)

bootstrap_theme = subproject('hotdoc_bootstrap_theme',
    default_options: [
        'less_include_path=@0@'.format(meson.current_source_dir() / 'less'),
        'install=true',
    ]
)

theme_dist_dir = bootstrap_theme.get_variable ('theme_dir')

subdir('core')
subdir('extensions')
subdir('parsers')
subdir('tests')
