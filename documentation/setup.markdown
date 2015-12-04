# Installation guide

To install hotdoc, you will first need to satisfy the dependencies, on fedora 22 this can be done with:

sudo dnf install glib2-devel flex python-devel libxml2-devel libxslt-devel clang-devel

And on ubuntu:

sudo apt-get install python-dev libglib2.0-dev flex libxml2-dev libxslt1-dev libclang-3.5-dev libgit2-dev

Adapt to your distribution.

You will also need to manually install the clang bindings adapted to your clang installation, for example if clang 3.5
is installed, you will need to run:

pip install clang==3.5

You can then install it through pypi with:

pip install hotdoc

It also works in a virtualenv.

# Configuration

Setting up or porting a project is very simple, just run:

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

## Incremental build

By default, rebuild is incremental, which vastly reduces the time needed to build
the documentation.

As this is still an experimental feature, if you wish to
rebuild everything at each run you can simply remove the "hotdoc-private" folder,
please file a bug if you have any reason to do that though.
