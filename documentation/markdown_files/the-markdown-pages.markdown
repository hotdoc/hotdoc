## The markdown pages

Where we present hotdoc's standalone markdown pages.

The standalone markdown files (usually located in "markdown_files) serve three main purposes:

* Actually holding documentation: the contents in all markdown files will get rendered with CommonMark nearly as is, with the exception of the [syntax extensions](syntax-extensions.markdown).

* Creating the site hierarchy, or site map, that is the way in which the various pages of the resulting documentation link to each other, starting from the provided index page. See the [link syntax extension documentation](syntax-extensions.markdown#link-syntax) for the complete description of how links may be defined.

* Optionally defining in which subpages source code symbols should be documented.

### Page creation tutorial

> The final output of this tutorial can be visited [here](https://people.collabora.com/~meh/simplest_example_hotdoc/html/index.html), and the final project is hosted [there](https://github.com/hotdoc/simplest_example), there is a Makefile that defines the `all` and `clean` targets.

The following instructions will help explaining a few concepts through example.

#### Set up a basic page tree

Set up a test folder

```
mkdir -p ~/hotdoc_layout_test/markdown_files
cd ~/hotdoc_layout_test
```

> Note: the directory for the markdown files doesn't need to be named `markdown_files`, and we don't actually need these files to be located in a separate subdirectory, but the former will hopefully become a convention and the latter is a recommended practice.

Now open `markdown_files/subpage.markdown` with the editor of your choice, put the following contents inside it and save it:

```
# Welcome to my subpage

Using *some* **random** `CommonMark` [syntax](http://spec.commonmark.org/)
```

Then open `markdown_files/index.markdown` with the editor of your choice, put the following contents inside it and save it:

```
# Welcome to my simple layout test project

### [My subpage](subpage.markdown)
```

You can now run hotdoc with

```
hotdoc --index markdown_files/index.markdown --output built_doc  run
```

from the `~/hotdoc_layout_test` folder, and check the output with `firefox built_doc/html/index.html`.

See the [configuration file section](the-configuration-file.markdown) if you'd like to convert this command-line to a configuration file.

A few things are to be noted here:

* Hotdoc will by default look for subpages in the folder where the provided index is located, so having `markdown_files/subpage.markdown` instead of `subpage.markdown` isn't necessary (and would not be recognized as a subpage anyway). Additional folders in which to look for documentation pages (but also code samples) can be provided to hotdoc with the `include-paths` configuration option.
* As you have guessed, when `index.markdown` is parsed, hotdoc will see that a page named `subpage.markdown` does exist in the `markdown_files` folder, it will thus open it and parse it in the same fashion, and consider `subpage.markdown` as a subpage of `index.markdown`.
* The process is of course repeated recursively, and its result is a documentation "tree", with its "root" being the `index.markdown` page and its only "leaf" (a page which doesn't have any subpages) being the `subpage.markdown` page
* Formatting is done in a latter stage, by walking through the documentation tree, and it's only at this moment that the destination of the link (`subpage.markdown`) is modified to point to the actual location of the output subpage (for example to `subpage.html`)

If all you want hotdoc to do is help you in generating a multi-page website from a set
of markdown files, then you can stop reading here.

If however you also want to use one or more hotdoc extensions to parse source code files and document the symbols that they contain, then keep on reading.

#### Assign sub-trees to language extensions

When hotdoc parses markdown sources, it attributes them an "extension-name". This name allows using language-specific formatters at format-time, amongst other things that extensions can customize. Of course an extension can choose to not provide a specific formatter, in which case the default formatter will be used.

> Note: this is (currently) the case for the C extension, which means that you can technically skip the rest of this section, as the default formatter will format symbols as C symbols.

The current approach for letting hotdoc know that a page and its subpages should be handled by a given extension is to create a separate "sub-index" file, link to it using a "well-known-name" instead of the raw filename in the desired parent page, and finally pass the raw filename to the chosen extension through the `*extension-prefix*-index` configuration option.

> Refer to the documentation of the extensions you're interested in to discover the well-known-names it has registered, and the exact command-line argument to use.

For example we could rework our previous example as such:

Replace the contents of `markdown_files/index.markdown` with

```
# Welcome to my documentation and API reference

### [My subpage](subpage.markdown)
### [Python API reference](python-api)
```

Then open `markdown_files/python_index.markdown` with the editor of your choice, put the following contents inside it and save it:

```
# Python API reference

This page, and all its (potential) subpages, will be formatted with the PythonHtmlFormatter, which is a subclass of the default HtmlFormatter.
```

Finally run hotdoc this way:

```
hotdoc --index markdown_files/index.markdown --output built_doc --python-index python_index.markdown run
```

Provided the [python extension](https://github.com/hotdoc/hotdoc_python_extension) is installed in the current environment, the `python_index.markdown` page will be rendered with the `PythonHtmlFormatter`, this is trivially verifiable with `grep "data-extension" built_doc/html/python_index.html`, which should show : `<div data-extension="python-extension" class="page_container" id="page-wrapper">`

> Note: In that example, the "well-known-name" is `python-api` and the command-line argument to let the extension know about the sub-index filename is `python-index`

#### Add symbols to pages

The next step will show how to include formatted source code symbols' documentation in the output.

The current approach to letting users define where to place the documentation for a given set of symbols is to have them explicitly list them as a bullet-list of empty links in the desired markdown page. The following steps will detail the process.

First open `module_to_document.py` with the editor of your choice, put the following contents inside it and save it:

```
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

Then, add the following to the bottom of `markdown_files/python-index.markdown`:

```

### [Module to document](explicit_list_of_symbols_in_python_module.markdown)
```

> This syntax doesn't expose any new concept, we're just defining a subpage in the standard way.

Finally, open `markdown_files/explicit_list_of_symbols_in_python_module.markdown` with the editor of your choice, put the following contents inside it and save it:

```
This is a module to demonstrate documenting source code symbols.

* [module_to_document.function_to_document]()
```

> When hotdoc encounters a link with an empty destination in a list item, it treats it as the name of a symbol to include in the containing page.

You can now invoke hotdoc with
```
hotdoc --index markdown_files/index.markdown --output built_doc --python-index python_index.markdown --python-sources module_to_document.py - run
```
, and check the result with `firefox built_doc/html/python_index.html`.

#### Or let extensions generate sub-trees and symbol lists

This approach of explicitly listing each symbol presents the advantage of letting users precisely define the page in which symbols will be documented, as well as their relative ordering,
however if they do not need this level of control, some extensions can generate the symbol's lists and sub-index themselves.

> Currently, only the python extension supports this, however generic support will be implemented pretty soon.

To have the extension generate these files, all you need to do is:

```
rm markdown_files/python_index.markdown
rm markdown_files/markdown_files/explicit_list_of_symbols_in_python_module.markdown
```

Then run hotdoc without specifying a `python-index`:

```
rm -rf hotdoc-private/ && hotdoc --index markdown_files/index.markdown --output built_doc --python-sources module_to_document.py - run
```

The result for that simple project should be strictly the same, you can find generated "intermediary" markdown pages in `hotdoc-private/generated`

> If you cloned <https://github.com/hotdoc/simplest_example> , you can checkout the "generated_symbol_list" branch to see this approach instead.
