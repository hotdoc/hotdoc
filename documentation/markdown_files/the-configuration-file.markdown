---
short-description: Where we present hotdoc's configuration file
...

# The configuration file

## Format

The configuration file is a simple, flat json file made of a set of key-value pairs, for example:

``` json
{
	"index": "markdown_files/index.markdown",
	"sitemap": "sitemap.txt",
	"project_name": "Foo",
	"project_version": "0.1"
}
```

is a valid hotdoc's configuration file. The valid keys are computed from the
command-line arguments, which you can list with `hotdoc help`.

The convention is to name this file `hotdoc.json`, when hotdoc is called it
will look for a file named that way in its invocation folder, use the
`--conf-file` command-line argument to specify an alternate path.

Options specified from the command-line will take precedence over their json counterpart.

## Creating from a command line invocation

An easy way to create a configuration file from a command-line invocation is to replace `run` with `conf` in the command-line, for example to translate:

``` shell
hotdoc --project-name "Foo" --project-version "0.1" --index markdown_files/index.markdown --output built_doc --sitemap sitemap.txt run
```

you should use 

``` shell
hotdoc --project-name "Foo" --project-version "0.1" --index markdown_files/index.markdown --output built_doc --sitemap sitemap.txt conf
```

This will create a hotdoc.json file in the current directory, which means you can now run hotdoc that way:

``` shell
hotdoc run
```
