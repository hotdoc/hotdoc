## Setting up a project

Guide for setting up a project.

Hotdoc can accept options both from the command line and from a json configuration file. The command line options will take precedence over their json counterpart. To see a list of all options available (including extension's options), run:

```
hotdoc help
```

> The current handling of the command line arguments is not entirely bullet-proof, as the intention was to provide a "git-like" interface, but the current implementation uses argparse.ArgumentParser.add_subparser, which doesn't lend itself very well to that use case, and some manual initial string manipulation is required.

### Setting up a project from scratch.

You will first need to create the markdown files that will constitute the "skeleton" of your documentation, see the [page creation tutorial](the-markdown-pages.markdown#page-creation-tutorial) for more information.

If you followed this tutorial up to its end you should now know how to structure your markdown files together and how to define in which pages individual source code symbols should be placed. If you need more inspiration, check out the [examples section](examples.markdown)
