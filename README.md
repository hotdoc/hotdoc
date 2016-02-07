![Hotdoc logo](https://cdn.rawgit.com/MathieuDuponchelle/hotdoc/develop/documentation/hotdoc.svg)

This project needs a logo. In the meantime, eyes will get hurt by this 
horrible illustration of programmer art.

* [Overview](#overview)
* [Features](#features)
  * [Incremental](#incremental)
  * [Simple yet powerful syntax](#simple-yet-powerful-syntax)
  * [Themeable output](#themeability)
  * [Exposes an API](#api)
  * [Smart inclusion syntax](#smart-inclusion-syntax)
* [Examples](#examples)
  * [Hotdoc's own bootstrapped documentation](#hotdocs-own-bootstrapped-documentation)
  * [A large GObject introspected C library](#a-large-gobject-introspected-c-library)
  * [A tiny test project](#a-tiny-test-project)
* [Installing](#installing)
  * [System-wide dependencies](#system-wide-dependencies)
  * [Virtualenv (strongly recommended)](#creating-a-virtualenv)
  * [Hotdoc itself](#hotdoc-itself)
* [Basic concepts and tutorials](#basic-concept-and-tutorials)
  * [The markdown pages](#the-markdown-pages)
    * [Page creation tutorial](#page-creation-tutorial)
      * [Set up a basic page tree](#set-up-a-basic-page-tree)
      * [Assign sub-trees to language extensions](#assign-sub-trees-to-language-extensions)
      * [Add symbols to pages](#add-symbols-to-pages)
      * [Or let extensions generate sub-trees and symbol lists](#or-let-extensions-generate-sub-trees-and-symbol-lists)
  * [The configuration file](#the-configuration-file)
    * [Creating from a command-line invocation](#creating-from-a-command-line-invocation)
  * [The quickstart wizard](#creating-with-the-quickstart-wizard)
* [Usage](#usage)
  * [Setting up a project]("#setting-up-a-project)
  * [Porting from an existing project](#porting-from-an-existing-project)
    * [Using the quickstart wizard](#using-the-quickstart-wizard)
    * [The manual way](#the-manual-way)
  * [Running](#running)
  * [Cleaning](#cleaning)
  * [Disabling incremental build](#disabling-incremental-build)

### Overview

Hotdoc is a documentation micro-framework. It provides an interface for
extensions to plug upon, along with some base objects (formatters, ...)

Please check the packages listed at [https://github.com/hotdoc](https://github.com/hotdoc) to
pick the extensions you are interested in.

### Features

#### Incremental

Hotdoc is designed as an incremental documentation system. Along with
its final output, it produces a database of symbols and a dependency
graph, which can be reused at the next run.

For example, [hotdoc_server](https://github.com/hotdoc/hotdoc_server) uses
hotdoc to provide (for now basic) wiki-like functionalities: users
can edit and preview the documentation, and the server patches the sources it was
extracted from.

> See [disabling incremental build](#disabling-incremental-build) if you do not wish / need to use this feature.

#### Simple yet powerful syntax

Hotdoc uses [CommonMark](http://commonmark.org/) to parse and render
standalone documentation pages.

This format was chosen because it is very simple to edit, yet allows
a great amount of control over the resulting layout, and the main
design requirement behind the choice of the format was to lower as
much as possible the barrier to contribute to documentation.

#### Themeability

The hotdoc html formatter supports theming. Its base output has
no stylesheets or scripts applied to it whatsoever, this is handled by themes,
which can additionally override the base templates. By default, hotdoc will use
a theme based on bootstrap and isotope, see
[https://github.com/hotdoc/hotdoc_bootstrap_theme](https://github.com/hotdoc/hotdoc_bootstrap_theme)
for its sources.

> Work is still ongoing on the default theme, a lot of its code needs to be
> placed in relevant extensions

#### API

Hotdoc 1.0 will expose a (reasonably) stable API, its intended users being:

* Extension writers, which will find the task of documenting a new language
  much easier than writing a tool from scratch.
* Application writers, which will be able to use it for all sorts of
  documentation-related tasks, ranging from retrieving the raw docstring
  for a given symbol, to showing a live preview during editing of any
  documentation snippet.

> See [the bootstraped documentation](#hotdocs-own-bootstrapped-documentation) to have a first taste of the API.

#### Smart inclusion syntax

Hotdoc extends the CommonMark syntax with the concept of transclusion, lifted
from MultiMarkdown. See [this page](http://talk.commonmark.org/t/transclusion-or-including-sub-documents-for-reuse/270>)
for the beginning of a discussion about having this feature in CommonMark itself.

The syntax is:

```
Please include {{ my_file }}
```

includes the file and parses it as markdown

```
Please include this subsection of my file {{ my_file[start:end] }}
```

includes the lines comprised between start and end and parse them as markdown.

```
Please include this symbol in my source code file { my_file.recognized_language_extension#symbol_name }
```

for example with `{ my_file.c#foo_bar }` , retrieves the symbol named `foo_bar` in `my_file.c` , and includes its content as a markdown code block. The range syntax can also be used in combination with this, for example { my_file.c#foo_bar[2:4] } will only include the lines 2 to 4 in the local scope of foo_bar.

> The file extension needs to be recognized and handled by a source code parsing hotdoc extension for this feature to work as described.

### Examples

#### Hotdoc's own bootstrapped documentation

> This is a *very* alpha work in progress, as the API isn't stable yet, docstrings are only partially filled out, and the python extension itself is also in an alpha state.

With the above warning taken into consideration, you can visit [this page]() to browse hotdoc's documentation.

#### A large GObject introspected C library

The documentation for the [glib](https://developer.gnome.org/glib/stable/), a fundamental GNOME C library, with "bindings" introspected for various languages can be browsed [here](https://people.collabora.com/~meh/glib_hotdoc/html/index.html)

The time to build it from scratch is currently around 20 seconds on my machine, 2-3 seconds to rebuild it when a random markdown page has been edited. Worst case scenario is approximately equal to the time
for building from scratch, for example when moving the `TRUE` symbol from one page to another, as it is referenced pretty much everywhere in the documentation.

#### A tiny test project

The documentation generated for a project that tries to use as much of hotdoc and its extension's features while staying as tiny as possible can be found [here](https://people.collabora.com/~meh/test_hotdoc_hotdoc/html/index.html), and its sources, which can be used as an example, live [there](https://github.com/hotdoc/test_hotdoc)

### Installing

#### System-wide dependencies

> If you install these dependencies successfully on a platform not listed here, or have issues on any platform, opening a simple issue (or a pull request with this file edited) will help immensely!

Hotdoc can optionally use [pygit2](http://www.pygit2.org/) to help with porting projects from other documentation systems.

If you wish to enable that feature, you need to install libgit2. On fedora this can be done with:

```
dnf install libgit2-devel.x86_64
```

And on ubuntu:

```
apt-get install libgit2-dev
```

Adapt to your distribution.

> If your installed version of libgit 2 is older than 0.22.0, this feature will not be enabled

Hotdoc also needs [graphviz](http://www.graphviz.org/) to generate object hierarchies, you will thus need to install graphviz-dev, and some libraries it depends depend on the python headers, so you will need to install them too.

On Fedora this can be done with:

```
dnf install graphviz-devel python-devel
```

And on ubuntu / debian:

```
apt-get install libgraphviz-dev python-dev
```

#### Creating a virtualenv

It is highly recommended to use [virtualenv](https://virtualenv.readthedocs.org/en/latest/) to try out any new python project, and hotdoc is no exception. You can however skip this step if you really do not
care about installing hotdoc system-wide.

> Assuming [pip](https://pip.pypa.io/en/stable/) is installed

```
pip install virtualenv
virtualenv hotdoc_env
. hotdoc_env/bin/activate
```

You are now in a virtual environment, to exit it you may call "deactivate", to enter it again simply call `. hotdoc_env/bin/activate` from the directory in which the environment was created.

#### Hotdoc itself

Two main alternatives are available:

* Using pip to get the last released version of hotdoc:
  ```
  pip install hotdoc
  ```

* Installing from a github clone:
  ```
  git clone https://github.com/hotdoc/hotdoc.git
  cd hotdoc
  python setup.py install
  ```

  > You can replace `install` with `develop` if you intend to edit the sources and do not want to run install again each time you want to test your modifications

Congratulations, you have successfully installed hotdoc! You may now want to check the [list of available extensions](https://github.com/hotdoc).

### Basic concepts and tutorials

#### The markdown pages

The standalone markdown files (usually located in "markdown_files) serve three main purposes:

* Actually holding documentation: the contents in all markdown files will get rendered with CommonMark nearly as is, with the exception of the [syntax extensions](#syntax-extensions).

* Creating the site hierarchy, or site map, that is the way in which the various pages of the resulting documentation link to each other, starting from the provided index page. See the [link syntax extension documentation](#link-syntax-extension) for the complete description of how links may be defined.

* Optionally defining in which subpages source code symbols should be documented.

##### Page creation tutorial

> The final output of this tutorial can be visited [here](https://people.collabora.com/~meh/simplest_example_hotdoc/html/index.html), and the final project is hosted [there](https://github.com/hotdoc/simplest_example), there is a Makefile that defines the `all` and `clean` targets.

The following instructions will help explaining a few concepts through example.

###### Set up a basic page tree

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
hotdoc --index markdown_files/index.markdown --output html  run
```

from the `~/hotdoc_layout_test` folder, and check the output with `firefox html/index.html`.

See the [configuration file section](#the-configuration-file) if you'd like to convert this command-line to a configuration file.

A few things are to be noted here:

* Hotdoc will by default look for subpages in the folder where the provided index is located, so having `markdown_files/subpage.markdown` instead of `subpage.markdown` isn't necessary (and would not be recognized as a subpage anyway). Additional folders in which to look for documentation pages (but also code samples) can be provided to hotdoc with the `include-paths` configuration option.
* As you have guessed, when `index.markdown` is parsed, hotdoc will see that a page named `subpage.markdown` does exist in the `markdown_files` folder, it will thus open it and parse it in the same fashion, and consider `subpage.markdown` as a subpage of `index.markdown`.
* The process is of course repeated recursively, and its result is a documentation "tree", with its "root" being the `index.markdown` page and its only "leaf" (a page which doesn't have any subpages) being the `subpage.markdown` page
* Formatting is done in a latter stage, by walking through the documentation tree, and it's only at this moment that the destination of the link (`subpage.markdown`) is modified to point to the actual location of the output subpage (for example to `subpage.html`)

If all you want hotdoc to do is help you in generating a multi-page website from a set
of markdown files, then you can stop reading here.

If however you also want to use one or more hotdoc extensions to parse source code files and document the symbols that they contain, then keep on reading.

###### Assign sub-trees to language extensions

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
hotdoc --index markdown_files/index.markdown --output html --python-index python_index.markdown run
```

Provided the [python extension](https://github.com/hotdoc/hotdoc_python_extension) is installed in the current environment, the `python_index.markdown` page will be rendered with the `PythonHtmlFormatter`, this is trivially verifiable with `grep "data-extension" html/python_index.html`, which should show : `<div data-extension="python-extension" class="page_container" id="page-wrapper">`

> Note: In that example, the "well-known-name" is `python-api` and the command-line argument to let the extension know about the sub-index filename is `python-index`

###### Add symbols to pages

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
hotdoc --index markdown_files/index.markdown --output html --python-index python_index.markdown --python-sources module_to_document.py - run
```
, and check the result with `firefox html/python_index.html`.

###### Or let extensions generate sub-trees and symbol lists

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
rm -rf hotdoc-private/ && hotdoc --index markdown_files/index.markdown --output html --python-sources module_to_document.py - run
```

The result for that simple project should be strictly the same, you can find generated "intermediary" markdown pages in `markdown_files/generated`

> If you cloned <https://github.com/hotdoc/simplest_example> , you can checkout the "generated_symbol_list" branch to see this approach instead.

#### The configuration file

The configuration file is a simple, flat json file made of a set of key-value pairs, for example:

```
{
    "html_theme": "default", 
    "output_format": "html"
}
```

is a valid hotdoc's configuration file. The valid keys are computed from the command-line arguments,
which you can list with `hotdoc help`.

The convention is to name this file `hotdoc.json`, when hotdoc is called it will look for a file named that way in its invocation folder, use the `--conf-file` command-line argument to specify an alternate path.

Options specified from the command-line will take precedence over their json counterpart.

##### Creating from a command line invocation

An easy way to create a configuration file from a command-line invocation is to replace `run` with `conf` in the command-line, for example to translate:

```
hotdoc --index markdown_files/index.markdown --output html run
```

you should use 

```
hotdoc --index markdown_files/index.markdown --output html conf
```

This will create a hotdoc.json file in the current directory, which means you can now run hotdoc that way:

```
hotdoc run
```

### Usage

#### Setting up a project

##### Porting from an existing project

Some extensions support creating a configuration file for projects that previously used a different documentation system, for example the "gobject-introspection" extension implements porting projects that previously used the `gtk-doc` suite of tools. Check the documentation for the extension relevant to your use case to learn more. If you wish to use such a porting tool, you'll need to [use the quickstart wizard](#using-the-quickstart-wizard)

Hotdoc can accept options both from the command line and from a json configuration file. The command line options will take precedence over their json counterpart. To see a list of all options available (including extension's options), run:

```
hotdoc hotdoc help --conf-file "plop.json"
```

> The current handling of the command line arguments is not entirely bullet-proof, as the intention was to provide a "git-like" interface, but the current implementation uses argparse.ArgumentParser.add_subparser, which doesn't lend itself very well to that use case, and some manual initial string manipulation is required.

##### Using the quickstart wizard

> The wizard is still pretty experimental, and a bit tedious to go through

Using the wizard is very simple, just run:

```
hotdoc conf --quickstart
```

And follow the instructions. By default, this will create a hotdoc.json file
in the current directory, you can specify an alternate path with --conf-file.

If all goes well, the documentation will be built in the same run.

To run the build again, you can use:

```
hotdoc run
```

You can edit the hotdoc.json file manually afterwards, and override any options
you set in there through the command-line (this can be useful for build system
integration, if you do not wish to hardcode C flags for example).

##### The manual way

You will first need to create the markdown files that will constitute the "skeleton" of your documentation, see the [page creation tutorial](#page-creation-tutorial) for more information.

If you followed this tutorial up to its end you should now know how to structure your markdown files together and how to define in which pages individual source code symbols should be placed. If you need more inspiration, check out the [examples section](#examples)

#### Running

Once a project has been [setup](#setting-up-a-project), building the documentation is trivial. You should either have a full command-line, in which case you can run it as is, or a configuration file named hotdoc.json in the folder where you intend to build the documentation, in which case you can simply run `hotdoc run`

#### Cleaning

Hotdoc generates its output in the specified directory, a folder named hotdoc-private in the folder it's run from, and a folder named `generated` in the folder where the global index is located.

Assuming the output directory is `html` and the index folder is `markdown_files`, a clean command would be:

```
rm -rf hotdoc-private generated html
```

#### Disabling incremental build

By default, rebuild is incremental, which vastly reduces the time needed to build
the documentation.

As this is still an experimental feature, if you wish to
rebuild everything at each run you can simply [clean](#cleaning) hotdoc's output beforehand,
please file a bug if you have any reason to do that though.
