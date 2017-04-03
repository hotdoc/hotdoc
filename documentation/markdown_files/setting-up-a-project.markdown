---
short-description: Minimal guide for setting up a project
...

# Setting up a project

Hotdoc can accept options both from the command line and from a json
configuration file. The command line options will take precedence over
their json counterpart.

To see a list of all options available (including extension's options), run:

``` shell
hotdoc help
```

## Setting up a project from scratch.

This will set up the project in the current directory:

```
hotdoc init
```

You can use `--init-dir` to specify a different directory, which will
be created:

```
hotdoc init --init-dir test
cd test
```

Once that's done:

```
hotdoc run
xdg-open built_doc/html/index.html
```

Refer to the
[page creation tutorial](the-markdown-pages.markdown#page-creation-tutorial)
for more information.

If you need more inspiration, check out the [other projects that use hotdoc](users.markdown)
