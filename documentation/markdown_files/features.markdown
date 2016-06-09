## Features

A non-extensive list of hotdoc features.

### Incremental

Hotdoc is designed as an incremental documentation system. Along with
its final output, it produces a database of symbols and a dependency
graph, which can be reused at the next run.

For example, [hotdoc_server](https://github.com/hotdoc/hotdoc_server) uses
hotdoc to provide (for now basic) wiki-like functionalities: users
can edit and preview the documentation, and the server patches the sources it was
extracted from.

> See [disabling incremental build](running.markdown#disabling-incremental-build) if you do not wish / need to use this feature.

### Simple yet powerful syntax

Hotdoc follows the [CommonMark](http://commonmark.org/) specification
and uses [cmark](https://github.com/jgm/cmark) to parse and render
standalone documentation pages.

This format was chosen because it is very simple to edit, yet allows
a great amount of control over the resulting layout, and the main
design requirement behind the choice of the format was to lower as
much as possible the barrier to contribute to documentation.

### Themeability

The hotdoc html formatter supports theming. Its base output has
no stylesheets or scripts applied to it whatsoever, this is handled by themes,
which can additionally override the base templates. By default, hotdoc will use
a theme based on bootstrap and isotope, see
[https://github.com/hotdoc/hotdoc_bootstrap_theme](https://github.com/hotdoc/hotdoc_bootstrap_theme)
for its sources.

### API

Hotdoc 1.0 will expose a (reasonably) stable API, its intended users being:

* Extension writers, which will find the task of documenting a new language
  much easier than writing a tool from scratch.
* Application writers, which will be able to use it for all sorts of
  documentation-related tasks, ranging from retrieving the raw docstring
  for a given symbol, to showing a live preview during editing of any
  documentation snippet.

> See [the bootstraped documentation](examples.markdown#hotdocs-own-bootstrapped-documentation) to get a first taste of the API.
