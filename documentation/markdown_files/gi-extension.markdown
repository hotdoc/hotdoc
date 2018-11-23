---
title: GI
short-description: Discover symbols in gir files
...

# GObject introspection extension

This extension parses the XML files produced by `g-ir-scanner`, the tool
implemented and maintained in [gobject-introspection] to discover symbols
exposed by an API.

Currently, this extension also requires the actual C source files to be
passed as arguments, as gir files miss two pieces of information hotdoc needs:

* The location of the documentation comments, to allow smart indexing to work on
  one hand, and emit detailed warnings when required on the other hand.

* The various defines and function macros exposed by a C API.

## Arguments



[gobject-introspection]: https://gitlab.gnome.org/GNOME/gobject-introspection
