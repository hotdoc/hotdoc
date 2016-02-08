## Features

### Incremental

Hotdoc is designed as an incremental documentation system. Along with
its final output, it produces a database of symbols and a dependency
graph, which can be reused at the next run.

For example, [hotdoc_server](https://github.com/hotdoc/hotdoc_server) uses
hotdoc to provide (for now basic) wiki-like functionalities: users
can edit and preview the documentation, and the server patches the sources it was
extracted from.

> See [disabling incremental build](disabling-incremental-build.markdown) if you do not wish / need to use this feature.

### Simple yet powerful syntax

Hotdoc uses [CommonMark](http://commonmark.org/) to parse and render
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

> Work is still ongoing on the default theme, a lot of its code needs to be
> placed in relevant extensions

### API

Hotdoc 1.0 will expose a (reasonably) stable API, its intended users being:

* Extension writers, which will find the task of documenting a new language
  much easier than writing a tool from scratch.
* Application writers, which will be able to use it for all sorts of
  documentation-related tasks, ranging from retrieving the raw docstring
  for a given symbol, to showing a live preview during editing of any
  documentation snippet.

> See [the bootstraped documentation](examples.markdown#hotdocs-own-bootstrapped-documentation) to get a first taste of the API.

### Smart inclusion syntax

Hotdoc extends the CommonMark syntax with the concept of transclusion, lifted
from MultiMarkdown. See [this page](http://talk.commonmark.org/t/transclusion-or-including-sub-documents-for-reuse/270>)
for the beginning of a discussion about having this feature in CommonMark itself.

The syntax is:

```
Please include \{\{ my_file \}\}
```

includes the file and parses it as markdown

```
Please include this subsection of my file \{\{ my_file[start:end] \}\}
```

includes the lines comprised between start and end and parse them as markdown.

```
Please include this symbol in my source code file \{\{ my_file.recognized_language_extension#symbol_name \}\}
```

for example with `{ my_file.c#foo_bar }` , retrieves the symbol named `foo_bar` in `my_file.c` , and includes its content as a markdown code block. The range syntax can also be used in combination with this, for example { my_file.c#foo_bar[2:4] } will only include the lines 2 to 4 in the local scope of foo_bar.

> The file extension needs to be recognized and handled by a source code parsing hotdoc extension for this feature to work as described.
