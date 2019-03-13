---
title: C
short-description: Discover symbols in C files with Clang
...

# C extension

The C extension can be used to parse C source files to extract comments and
symbols.

## Dependencies

The extension uses [Clang] to build and walk an AST from the source code, as
such it is necessary for the build environment to allow its compilation, and
arguments are exposed to allow specifying the C flags and / or the names of the
dependencies that C flags should be obtained from using [pkg-config].

On a Debian-based OS you will need to install `llvm` and `libclang-dev` packages.

## Commment parser

Currently, comments are expected to be formatted according to the [gtk-doc syntax].

## Arguments

This extension exposes the following arguments / configuration options:

* `--c-index`, `c_index`: Name of the root markdown file, which can be None. See
  [](the-smart-index.markdown) for more information.

* `--c-include-directories`, `c_include_directories`: List of include directories, equivalent
  to clang's `-I`

* `--pkg-config-packages`, `pkg_config_packages`: List of packages the library depends upon

* `--extra-c-flags`, `extra_c_flags`: Extra flags to use when compiling, eg `-D`, `-U`

* `--c-index`, `c_index`: Optional path to a markdown file that will be parsed and used
  as the index for the extension in the sitemap. If not specified, an empty page will be
  generated.

* `--c-sources`, `c_sources`: List of sources to parse, can contain patterns which
  will be passed through [glob]

* `--c-source-filters`, `c_source_filters`: List of sources to exclude, can contain
  patterns which will be passed through [glob]. This is useful when passing patterns
  to `c_sources`

* `--c-source-roots`, `c_source_roots`: List of root directories paths should be
  made relative to. This is useful when generated sources are documented, to avoid
  ending up with an unnecessarily deep sitemap.

[gtk-doc syntax]: https://developer.gnome.org/gtk-doc-manual/stable/documenting_syntax.html.en
[Clang]: https://clang.llvm.org/
[glob]: https://docs.python.org/3/library/glob.html
[pkg-config]: https://www.freedesktop.org/wiki/Software/pkg-config/
