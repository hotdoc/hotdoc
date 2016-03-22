## Examples

A list of example projects using hotdoc.

### Hotdoc's own bootstrapped documentation

> This is a *very* alpha work in progress, as the API isn't stable yet, docstrings are only partially filled out, and the python extension itself is also in an alpha state.

You're looking at it, check <https://github.com/hotdoc/hotdoc/tree/master/documentation> for the sources.

### A large GObject introspected C library

The documentation for the [glib](https://developer.gnome.org/glib/stable/), a fundamental GNOME C library, with "bindings" introspected for various languages can be browsed [here](https://people.collabora.com/~meh/glib_hotdoc/html/index.html)

The time to build it from scratch is currently around 20 seconds on my machine, 2-3 seconds to rebuild it when a random markdown page has been edited. Worst case scenario is approximately equal to the time
for building from scratch, for example when moving the `TRUE` symbol from one page to another, as it is referenced pretty much everywhere in the documentation.

### A tiny test project

The documentation generated for a project that tries to use as much of hotdoc and its extension's features while staying as tiny as possible can be found [here](https://people.collabora.com/~meh/test_hotdoc_hotdoc/html/index.html), and its sources, which can be used as an example, live [there](https://github.com/hotdoc/test_hotdoc)
