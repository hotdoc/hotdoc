cmark_opts = cmake.subproject_options()
cmark_opts.add_cmake_defines({'CMARK_STATIC': true})
cmark_opts.add_cmake_defines({'CMARK_SHARED': false})
cmark_opts.add_cmake_defines({'CMARK_TESTS': false})
cmark_opts.set_install(false)
cmark_subproj = cmake.subproject('cmark', options: cmark_opts)

cmark_lib = cmark_subproj.dependency('libcmark_static')
cmarkextensions_lib = cmark_subproj.dependency('cmarkextensions_static')

py.extension_module('cmark',
    'cmark_module.c',
    'cmark_gtkdoc_extension.c',
    'cmark_gtkdoc_scanner.c',
    'cmark_include_extension.c',
    'cmark_include_scanner.c',
    dependencies: [cmark_lib.as_link_whole(), cmarkextensions_lib.as_link_whole()],
    install: true,
    subdir: 'hotdoc/parsers',
)

py.extension_module('search',
    'search_module.c',
    'trie.c',
    dependencies: [
        dependency('glib-2.0'),
        dependency('libxml-2.0'),
        dependency('json-glib-1.0'),
    ],
    install: true,
    subdir: 'hotdoc/parsers',
)

py.install_sources(
    'cmark_utils.py',
    'gtk_doc.py',
    '__init__.py',
    'sitemap.py',
    'tests/__init__.py',
    'tests/test_cmark_parser.py',
    'tests/test_standalone_parser.py',
    'c_comment_scanner/__init__.py',
    subdir: 'hotdoc/parsers',
    preserve_path: true,
)

subdir('c_comment_scanner')