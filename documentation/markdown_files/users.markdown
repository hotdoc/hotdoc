---
short-description: A list of projects using hotdoc
...

# Examples

## Hotdoc's own bootstrapped documentation

> This is a *very* alpha work in progress, as the API isn't stable yet, docstrings are only partially filled out, and the python extension itself is also in an alpha state.

You're looking at it, check <https://github.com/hotdoc/hotdoc/tree/master/documentation> for the sources.

## GStreamer's documentation

GStreamer's [documentation](https://gstreamer.freedesktop.org/documentation/) has been ported from docbook to hotdoc + markdown. Its API reference is currently being ported as well, using hotdoc's subproject nesting capabilities.

## Apertis' documentation

[Apertis](https://docs.apertis.org/) is a Debian-based distribution for In-Vehicle-Infotainment. The documentation for its individual libraries is currently listed with the default HTTP index, it will hopefully be ported to use hotdoc's nested subprojects at some point.

## Endless Modular Framework documentation ##

The [app development platform for Endless OS](http://endlessm.github.io/eos-knowledge-lib/) uses hotdoc for the [documentation](http://endlessm.github.io/eos-knowledge-lib/docs/master/) for its user interface tools. This hotdoc project uses a [custom extension](https://github.com/endlessm/hotdoc-modular-framework).

## A tiny test project

The documentation generated for a project that tries to use as much of hotdoc and its extension's features while staying as tiny as possible can be found [here](https://people.collabora.com/~meh/test_hotdoc/), and its sources, which can be used as an example, live [there](https://github.com/hotdoc/test_hotdoc)
