# Installation guide

Hotdoc can optionally use pygit2 to help with porting projects from other documentation systems.

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

Hotdoc also needs graphviz to generate object hierarchies, you will thus need to install graphviz-dev

On Fedora this can be done with:

```
dnf install graphviz-devel
```

And on ubuntu / debian:

```
apt-get install libgraphviz-dev
```

You can then install hotdoc through pypi with:

```
pip install hotdoc
```

It also works in a virtualenv.

Hotdoc is a documentation micro-framework, as such the hotdoc package isn't very useful by itself.

To find extensions you may be interested in, check https://github.com/hotdoc .

For example, if you want to document GObject introspected code, you'll want to install hotdoc_gi_extension,
which will pull hotdoc_c_extension as it depends on it.

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
