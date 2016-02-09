## Extensions to the CommonMark syntax

### Link syntax

The syntax for a "classic link" in markdown is:

```
[link label goes here](link-destination-there)
```

Hotdoc will make some additional checks on the link destination, and handle the following cases:

#### Subpage parsing

```
# [My subpage](my_subpage.markdown)
```

If:

* the link is part of a header, the `#` in this example, can be any level so `####` will work too
* the destination it points to is a file that exists in one of the include paths (the directory of the main index, and the directories passed with `--include-paths`)

Then a subpage is added to the containing page, and the link is modified at format time to point to the actual output, in this example if the output format is `.html`, then the result will be:

```
<a href="my_subpage.html">My subpage</a>
```

and "my_subpage.markdown" will be recursively parsed and formatted in the same fashion.

#### Well-known-name parsing

```
# [My subpage](example-api)
```

If:

* the link is part of a header, the `#` in this example, can be any level so `####` will work too
* the destination it points to is a valid "well-known-name", as registered by an extension

Then the creation of the subtree will be handled by an extension, with the sub-index being provided through the command-line, typically with `extension-name-index`.

This mechanism allows us to use different formatters for different subtrees, in our example if:

* An extension exists named example, which exposes an `example-extension-index` command line option and has registered the `example-api` well-known-name
* Hotdoc is called with `hotdoc run [...] --example-extension-index=example-index.markdown`
* A markdown file named `example-index.markdown` exists in the include paths

then the same mechanism as classic subpage parsing occurs, except that the subpages will be created by the extension, which will for example allow it to use a different formatter.

Using a different formatter means for example that the python extension can format prototypes differently, amongst other things.

#### Listing symbols that have to be documented in a given page

```
* [my_symbol_name]()
```

If:

* the link is part of a bullet list, denoted by the `*` symbol
* the destination of the link is empty

Then hotdoc will treat the symbol label as the name of a symbol to include in the containing page.

#### Referencing a symbol

```
[any label](my_symbol_name)
```

If `my_symbol_name` is recognized as a valid symbol, then at format time the destination will be modified to point to the url of this symbol's documentation.

> The label can be empty, in which case it will be set to the name of the symbol at format time

#### Referencing another page

```
[any label](my_other_page.markdown)
```

If `my_other_page.markdown` is a known subpage, then the destination will be updated to point to its url at format time. This differs from the subpage parsing in that `my_other_page.markdown` will neither be considered as a subpage, nor parsed, in order not to interfere with the definition of the site "hierarchy".

If the `--html-add-anchors` configuration is set to True, then a simple script is added to all the pages, which adds an `id` attribute to all header links that don't have one, with its value set as the value of the title, lowercased and with whitespaces replaced by hyphens (`-`).

This means that given this page named `referenced.markdown`:

```
# My title

### My subsection
```

One can link to `My subsection` in a different page like this:

```
See [this subsection](referenced.markdown#my-subsection) for more details.
```

### Smart file inclusion syntax

Hotdoc extends the CommonMark syntax with the concept of transclusion, lifted
from MultiMarkdown. See [this page](http://talk.commonmark.org/t/transclusion-or-including-sub-documents-for-reuse/270>)
for the beginning of a discussion about having this feature in CommonMark itself.

The syntax is:

```
Please include {{ my_file.markdown }}
```

includes the file and parses it as markdown, if the extension is either `.markdown` or `.md`. Any other extension (or lack of), will be included in a code block.

```
Please include this subsection of my file {{ my_file.markdown[start:end] }}
```

includes the lines comprised between start and end and parses them as markdown.

```
Please include this symbol in my source code file {{ my_file.recognized_language_extension#symbol_name }}
```

for example with `{{ my_file.c#foo_bar }}` , retrieves the symbol named `foo_bar` in `my_file.c` , and includes its content as a markdown code block. The range syntax can also be used in combination with this, for example {{ my_file.c#foo_bar[2:4] }} will only include the lines 2 to 4 in the local scope of foo_bar.

> The file extension needs to be recognized and handled by a source code parsing hotdoc extension for this feature to work as described.
