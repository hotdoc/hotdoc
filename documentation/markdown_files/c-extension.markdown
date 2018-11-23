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

## Arguments

This extension exposes the following arguments:

* `--c-index`: Name of the root markdown file, which can be None. See
  []the-smart-index.markdown] for more information.

* `--c-include-directories`: List of include directories, equivalent to gcc's `-I`

* `--pkg-config-packages`: List of packages the library depends upon

* `--extra-c-flags`: Extra flags to use when compiling, eg `-D`, `-U`

[Clang]: https://clang.llvm.org/
[pkg-config]: https://www.freedesktop.org/wiki/Software/pkg-config/
