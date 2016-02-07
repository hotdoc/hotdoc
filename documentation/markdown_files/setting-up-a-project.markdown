## Setting up a project

### Porting from an existing project

Some extensions support creating a configuration file for projects that previously used a different documentation system, for example the "gobject-introspection" extension implements porting projects that previously used the `gtk-doc` suite of tools. Check the documentation for the extension relevant to your use case to learn more. If you wish to use such a porting tool, you'll need to [use the quickstart wizard](#using-the-quickstart-wizard)

Hotdoc can accept options both from the command line and from a json configuration file. The command line options will take precedence over their json counterpart. To see a list of all options available (including extension's options), run:

```
hotdoc hotdoc help --conf-file "plop.json"
```

> The current handling of the command line arguments is not entirely bullet-proof, as the intention was to provide a "git-like" interface, but the current implementation uses argparse.ArgumentParser.add_subparser, which doesn't lend itself very well to that use case, and some manual initial string manipulation is required.

### Using the quickstart wizard

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

### The manual way

You will first need to create the markdown files that will constitute the "skeleton" of your documentation, see the [page creation tutorial](#page-creation-tutorial) for more information.

If you followed this tutorial up to its end you should now know how to structure your markdown files together and how to define in which pages individual source code symbols should be placed. If you need more inspiration, check out the [examples section](#examples)
