![Hotdoc logo](https://cdn.rawgit.com/MathieuDuponchelle/hotdoc/develop/documentation/hotdoc.svg)

This project needs a logo. In the meantime, eyes will get hurt by this 
horrible illustration of programmer art.

Read [this](documentation/setup.markdown) if you just want to use hotdoc.

###Overview

Hotdoc is a documentation micro-framework. It provides an interface for
extensions to plug upon, along with some base objects (formatters, ...)

Hotdoc is also designed as an incremental documentation system. Along with
its final output, it also produces a database of symbols and a dependency
graph, which can be reused at the next run, or queried upon externally.

For example, [hotdoc_server](https://github.com/hotdoc/hotdoc_server) uses
hotdoc to provide (for now basic) wiki-like functionalities: users
can edit and preview the documentation, and the server patches the sources it was
extracted from.

Please check the packages listed at [https://github.com/hotdoc](https://github.com/hotdoc) to
pick the extensions you are interested in.

Hotdoc currently uses CommonMark to parse and render standalone documentation markdown pages,
and implements some custom parsing of links on top. It would be possible to
override this default parser in an extension, for example to use pandoc, or modify
the parsing.

Lastly, the hotdoc html formatter also supports theming. Its base output has
no stylesheets or scripts applied to it whatsoever, this is handled by themes,
which can additionally override the base templates. By default, hotdoc will use
a theme based on bootstrap and isotope, see
[https://github.com/hotdoc/hotdoc_bootstrap_theme](https://github.com/hotdoc/hotdoc_bootstrap_theme)
for its sources.
