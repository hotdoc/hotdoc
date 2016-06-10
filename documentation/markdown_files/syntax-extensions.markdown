---
short-description: Where we present hotdoc's extensions to the CommonMark specification
...

# Extensions to the CommonMark syntax

## Link syntax

The syntax for a "classic link" in markdown is:

``` markdown
[link label goes here](link-destination-there)
```

Hotdoc will make some additional checks on the link destination, and handle the
following cases:

### Referencing a symbol

``` markdown
[any label](my_symbol_name)
```

If `my_symbol_name` is recognized as a valid symbol, then at format time the
destination will be modified to point to the url of this symbol's
documentation.

> The label can be empty, in which case it will be set to the name of the
> symbol at format time

### Referencing another page

``` markdown
[any label](my_other_page.markdown)
```

If `my_other_page.markdown` is a known subpage, then the destination will be
updated to point to its url at format time.

Hotdoc also adds an `id` attribute to all header links that don't have one,
with its value set as the value of the title, lowercased, with whitespaces
replaced by hyphens (`-`), and all non-ASCII characters stripped away, as well
as characters forbidden in ids such as `/`.

This means that given this page named `referenced.markdown`:

``` markdown
# My title

## My subsection
```

One can link to `My subsection` in a different page like this:

``` markdown
See [this subsection](referenced.markdown#my-subsection) for more details.
```

If the link is made in the same page, one can also use an empty link label,
which will get replaced by the contents of the title at format-time.

## Smart file inclusion syntax

Hotdoc extends the CommonMark syntax with the concept of transclusion, lifted
from MultiMarkdown. See
[this page](http://talk.commonmark.org/t/transclusion-or-including-sub-documents-for-reuse/270>)
for the beginning of a discussion about having this feature in CommonMark
itself.

The syntax is:

``` markdown
Please include {{ my_file.markdown }}
```

includes the file and parses it as markdown, if the extension is either
`.markdown` or `.md`. Any other extension (or lack of), will be included
in a code block.

``` markdown
Please include this subsection of my file {{ my_file.markdown[start:end] }}
```

includes the lines comprised between start and end and parses them as markdown.

``` markdown
Please include this symbol from my source code file {{ my_file.recognized_language_extension#symbol_name }}
```

for example with `{{ my_file.c#foo_bar }}`, retrieves the symbol named
`foo_bar` in `my_file.c`, and includes its content as a markdown code block.
The range syntax can also be used in combination with this, for example
`{{ my_file.c#foo_bar[2:4] }}` will only include the lines 2 to 4 in the
local scope of `foo_bar`.

> The file extension needs to be recognized and handled by a source code
> parsing hotdoc extension for this feature to work as described.

## Piped tables syntax

Tables are one of the [most demanded][tables discussion] feature that is still
currently lacking in the CommonMark specification.

I have [proposed][extension proposal] a pretty intrusive patch (but obviously
perfectly correct ^^) to add extension support in libcmark, however getting
it upstream is pretty involved, and having the new version of cmark packaged
in major linux distributions will also take time.

In the meantime, my modified version of cmark is [bundled] in hotdoc
(I know D: ), and supports a simple version of piped tables:

``` markdown
| Header 1 | Header 2 |
| -------- | -------- |
| Content  | Content  |
```

This is recognized as a table with two header cells, and a row containing
two cells.

The include extension is also implemented this way.

[tables discussion]: https://talk.commonmark.org/t/tables-in-pure-markdown/81/92

[extension proposal]: https://github.com/jgm/cmark/pull/123

[bundled]: https://github.com/MathieuDuponchelle/cmark/tree/d71d4a395e73762ee1c2b8cf147fd30fb3a78cb0
