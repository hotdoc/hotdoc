---
short-description: Guide for building a hotdoc project.
...

# Running

Once a project has been [setup](setting-up-a-project.markdown), building the
documentation is trivial. You should either have a full command-line, in
which case you can run it as is, or a configuration file named `hotdoc.json` in
the folder where you intend to build the documentation, in which case you can
simply run `hotdoc run`

## Disabling incremental build

By default, rebuild is incremental, which vastly reduces the time needed to
build the documentation.

As this is still an experimental feature, if you wish to rebuild everything at
each run you can simply [clean](cleaning.markdown) hotdoc's output beforehand,
please file a bug if you have any reason to do that though.
