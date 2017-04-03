---
short-description: Where we present hotdoc's markdown pages
...

# The markdown pages

The standalone markdown files (usually located in `markdown_files`) serve
two main purposes:

* Actually holding documentation: the contents in all markdown files will
  get rendered following the [CommonMark] specification nearly as is,
  with the exception of the [syntax extensions](syntax-extensions.markdown).

* Holding metadata in [yaml] headers.

## Page creation tutorial

> The final output of this tutorial can be visited
> [here](https://people.collabora.com/~meh/simplest_example/index.html),
> and the final project is hosted [there](https://github.com/hotdoc/simplest_example),
> it contains a Makefile defining the `all` and `clean` targets.

The following instructions will help explaining a few concepts through example.

### Setting up a basic page tree

Set up a test folder

``` shell
mkdir -p ~/hotdoc_layout_test/markdown_files
cd ~/hotdoc_layout_test
```

> Note: the directory for the markdown files doesn't need to be named `markdown_files`, and we don't actually need these files to be located in a separate subdirectory, but the former will hopefully become a convention and the latter is a recommended practice.

Now open `markdown_files/subpage.markdown` with the editor of your choice, put the following contents inside it and save it:

``` markdown
---
short-description: Just a subpage
...

# My subpage

Using *some* **random** `CommonMark` [syntax](http://spec.commonmark.org/)

You may want to go back to [the index](index.markdown) now?
```

Then open `markdown_files/index.markdown` with the editor of your choice, put the following contents inside it and save it:

``` markdown
# My project
```

Finally open `sitemap.txt`, input the following contents and save it:

``` txt
index.markdown
	subpage.markdown
```

You can now run hotdoc with

``` shell
hotdoc --index markdown_files/index.markdown --output built_doc --project-name "simplest-example" --project-version "0.1" --sitemap sitemap.txt run
```

from the `~/hotdoc_layout_test` folder, and check the output with `xdg-open built_doc/html/index.html`.

See the [configuration file section](the-configuration-file.markdown) if you'd like to convert this command-line to a configuration file.

A few things are to be noted here:

* Hotdoc will by default look for subpages in the folder where the provided
  index is located, so only the basenames need to be input in the sitemap.
  Additional folders in which to look for documentation pages (but also code
  samples) can be provided to hotdoc via the `include-paths`
  configuration option.

* Links to pages in the doc tree are updated at format-time, in our example
  `index.markdown` will be updated to `index.html` when outputting html.

* The metadata in the yaml headers is not directly visible in the pages
  they document, but it is used when presenting subpages. In our case,
  we did not provide any `title` metadata, so the title picked for
  our subpage is the first heading found in the page. Try defining
  the `title` metadata in the yaml header if that's your thing :)

If all you want hotdoc to do is help you in generating a multi-page website
from a set of markdown files, then you can stop reading this page, throw an
eye at [this page](the-configuration-file.markdown) and
[this one too](syntax-extensions.markdown) though, can't hurt.

If however you also want to use one or more hotdoc extensions to parse source
code files and document the symbols that they contain, then keep on reading.

### Assigning sub-trees to language extensions

When hotdoc parses markdown sources, it attributes them an "extension-name". This name allows using language-specific formatters at format-time, amongst other things that extensions can customize. Of course an extension can choose to not provide a specific formatter, in which case the default formatter will be used.

> Note: this is (currently) the case for the C extension, which means
> that you can technically skip the rest of this section if C is your use 
> case, as the default formatter will format symbols as C symbols.

The current approach for letting hotdoc know that a page and its subpages
should be handled by a given extension is to create a separate "sub-index"
file, use a "well-known-name" placeholder in the sitemap instead of the raw
filename, and finally pass the raw filename to the chosen extension
through the `*extension-prefix*-index` configuration option.

For example we could rework our previous example as such:

Open `markdown_files/python_index.markdown` with the editor of your choice, put the following contents inside it and save it:

``` markdown
---
short-description: Just an API
...

# Python API reference

This page, and all its (potential) subpages, will be formatted with the
PythonHtmlFormatter, which is a subclass of the default HtmlFormatter.
```

Update `sitemap.txt` to:

``` txt
index.markdown
	subpage.markdown
	python-index
```

Finally run hotdoc this way:

``` shell
hotdoc --index markdown_files/index.markdown --output built_doc --project-name "simplest-example" --project-version "0.1" --python-index python_index.markdown --sitemap sitemap.txt run -vv
```

Note that the two pages you created earlier are not reparsed, nor
reformatted. This only presents a very theoretical advantage in our case,
but this can come in quite handy when managing hundreds of pages.

Provided the [python extension] is installed in the current environment,
the `python_index.markdown` page will be rendered with the
`PythonHtmlFormatter`, this is trivially verifiable with
`grep "data-extension" built_doc/html/python_index.html`, which should show :
`<div data-extension="python-extension" class="page_container" id="page-wrapper">`

In that example, the "well-known-name" is `python-index` and the
command-line argument to let the extension know about the sub-index filename
is `python-index` too. The path for the sub-index will be treated
as relative to the main index.

You can of course have the python index be the top level index in the
sitemap.

### Add symbols to pages

The next step will show how to include formatted source code symbols'
documentation in the output.

The current approach to letting users define where to place the documentation
for a given set of symbols is to have them explicitly listed in
the page's metadata. The following steps will detail the process.

First open `module_to_document.py` with the editor of your choice, put the following contents inside it and save it:

``` python
def function_to_document(foo, bar):
    """A function to document

    This is just a simple addition function.

    Args:
        foo: int, The first operand of the addition
        bar: int, The other operand of the addition
    Returns:
        int: The addition of `foo` and `bar`
    """
    return foo + bar
```

Then, edit `sitemap.txt` to:

``` txt
index.markdown
	subpage.markdown
	python-index
		explicit_list_of_symbols_in_python_module.markdown
```

> This syntax doesn't expose any new concept, we're just defining a subpage
> in the standard way.

Finally, open `markdown_files/explicit_list_of_symbols_in_python_module.markdown`
with the editor of your choice, put the following contents inside it and save it:

``` markdown
---
short-description: Just a python module
symbols:
    - module_to_document.function_to_document
...

# My module

This is a module to demonstrate documenting source code symbols.
```

You can now invoke hotdoc with

``` shell
hotdoc --index markdown_files/index.markdown --output built_doc --project-name "simplest-example" --project-version "0.1" --python-index python_index.markdown --python-sources module_to_document.py --sitemap sitemap.txt run
```
, and check the result with `xdg-open built_doc/html/python_index.html`.

### Or let extensions generate sub-trees and symbol lists

This approach of explicitly listing each symbol presents the advantage of
letting users precisely define the page in which symbols will be documented,
as well as their relative ordering, however if they do not need this level
of control, all extensions can generate the symbol's lists and sub-index
themselves.

To have the extension generate these files, all you need to do is:

``` shell
rm markdown_files/python_index.markdown
rm markdown_files/markdown_files/explicit_list_of_symbols_in_python_module.markdown
```

and edit the sitemap back to:

``` txt
index.markdown
	subpage.markdown
	python-index
```

Then run hotdoc without specifying a `python-index`:

``` shell
rm -rf hotdoc-private* && hotdoc --index markdown_files/index.markdown --output built_doc --python-sources module_to_document.py --python-smart-index --sitemap sitemap.txt run
```

> Removing the `hotdoc-private` folder ensures we rebuild from scratch,
> just to prove our point.

> Also note the --python-smart-index argument.

The result for that simple project should be strictly the same, you can find generated "intermediary" markdown pages in `hotdoc-private/generated`

> If you cloned <https://github.com/hotdoc/simplest_example> , you can checkout the "generated_symbol_list" branch to see this approach instead.

### Advanced layout

The two approaches listed above can be mixed, this will soon<sup>(tm)</sup> be documented.

[yaml]: http://yaml.org/

[CommonMark]: http://commonmark.org/

[python extension]: https://github.com/hotdoc/hotdoc_python_extension
