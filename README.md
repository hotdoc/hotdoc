![Hotdoc logo](https://cdn.rawgit.com/MathieuDuponchelle/hotdoc/develop/documentation/hotdoc.svg)

This project needs a logo. In the meantime, eyes will get hurt by this 
horrible illustration of programmer art.

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
* Themeability (see [this example](https://github.com/MathieuDuponchelle/hotdoc_bootstrap_theme/commits/master)
* Persisting of the documentation through sqlalchemy, with an API to access it.
  An example project that uses this API is the hotdoc server, which will soon be made public.
+ Many more things !

### Additional resources (FIXME: update extensions, outdated)

Check out the [HotDoc extensions](https://github.com/MathieuDuponchelle/hotdoc_extensions)
