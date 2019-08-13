subdir('c_comment_scanner')

modules += [python.extension_module('cmark',
    'cmark_module.c',
    'cmark_gtkdoc_extension.c',
    'cmark_gtkdoc_scanner.c',
    'cmark_include_extension.c',
    'cmark_include_scanner.c',
    dependencies: [python.dependency(), cmark_dep, cmarkextension_dep],
    subdir: 'hotdoc/parsers',
    install: true)]

glib_req_version = '>= 2.44.0'
json_glib_req_version = '>= 1.2'
glib_dep = dependency('glib-2.0', version: glib_req_version, fallback: ['glib', 'libglib_dep'])
json_glib_dep = dependency('glib-2.0', fallback: ['glib', 'libglib_dep'])
json_dep = dependency('json-glib-1.0',
    fallback : ['json-glib', 'json_glib_dep'])
libxml_dep = dependency('libxml-2.0', fallback: ['libxml2', 'xml2lib_dep'])

modules += [python.extension_module('search',
    'search_module.c',
    'trie.c',
    dependencies: [python.dependency(), glib_dep, json_dep, libxml_dep],
    subdir: 'hotdoc/parsers',
    install: true)]

foreach f: ['cmark_utils.py', 'gtk_doc.py', '__init__.py', 'sitemap.py',]
    python.install_sources(f, pure: false, subdir: 'hotdoc/parsers')
    to_symlink += [[meson.current_source_dir() / f, meson.current_build_dir() / f]]
endforeach