% Overview of the dependencies
% Mathieu Duponchelle
% July 26, 2015

At Runtime:
-----------

* python (mandatory)

* python dagger for dependency checks (optional)

* CommonMark

* the python bindings for libclang, version still to specify
  (we might end up bundling them as the API doesn't seem very stable)
  (mandatory for C / C++)

* Some sort of database adapter, still to be determined (optional)

* The python lxml package (mandatory)

* gobject-introspection for its comment block parser (ugly, make that unneeded)

At BuildTime:
-------------

* The python headers, flex and a C compiler for fast comment
  block lexing (mandatory)
