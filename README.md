# HotDoc

*The tastiest documentation system*

Read [this](documentation/setup.markdown) if you just want to use hotdoc.

###Overview

HotDoc aims at being a highly modular API documentation tool / library for
C and C++ libraries (initially).

It is based on clang for the source code parsing, and CommonMark for the
formatting.

It was previously based on pandoc, and a pandoc backend will be available
again soon, but the dependency tree with a hard pandoc dependency was just too
deep.

It features:

+ An incremental build system, that only rebuilds the output depending on the changed
  resources
+ A pretty comprehensive extension system, handmade and bound to be subjected to API
  breakage until the 1.0 version of hotdoc is released
+ A built-in gobject-introspection extension, which will expose gobject-specific
  concepts (properties, signals, annotations ...)
+ Many more things !

### Interesting resources

* [Overview of the rendering design](documentation/design.markdown)
* [Dependencies](documentation/dependencies.markdown)
* [Porting from gtk-doc](documentation/porting.markdown)

### Additional resources

Check out the [HotDoc extensions](https://github.com/MathieuDuponchelle/hotdoc_extensions)
