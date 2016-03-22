## Porting guide(s)

Collection of porting guides.

Some extensions support creating a configuration file for projects that previously used a different documentation system, for example the "gobject-introspection" extension implements porting projects that previously used the [gtk-doc](http://www.gtk.org/gtk-doc/) suite of tools.

### Gtk-doc Porting Guide

This section will walk you through the process for porting a project from [gtk-doc](http://www.gtk.org/gtk-doc/) to hotdoc.

The [gi-extension](https://github.com/hotdoc/hotdoc_gi_extension) provides two helper scripts that largely automate this task, the following is an example of porting [gcr](https://git.gnome.org/browse/gcr/).

#### Requirements

* Hotdoc and the hotdoc-gi-extension have to be installed and available in the environment.
* [Pandoc](http://pandoc.org/) has to be installed on the system, preferably a version recent enough, offering the commonmark output format, this is verifiable with `pandoc -h | grep "commonmark"`. If it isn't available, the porting scripts will fall back to github markdown, or strict markdown.
* [Git](https://git-scm.com/) has to be installed as well, as one of the porting scripts uses it to check whether some files are under version control or not.
* [Gtk-doc](http://www.gtk.org/gtk-doc/) itself has to be available on the system too.

#### Build the library with gtk-doc enabled

For this example, the gcr sources have to be available, and it needs to build successfully in the environment, with gtk-doc enabled:

```
git clone git://git.gnome.org/gcr
cd gcr
./autogen.sh --enable-gtk-doc
make
```

#### Set up the hotdoc folder

For simplicity, we will create a hotdoc directory right next to the gtk-doc directory. This directory is usually located under doc/reference, or doc/reference/library_name. In the first case we would run:

```
mkdir doc/hotdoc_reference
```

and in the second case:

```
mkdir doc/reference/hotdoc_library_name
```

Cgr is in the second category, we thus run:

```
mkdir doc/reference/hotdoc_cgr
```

and we navigate there:

```
cd doc/reference/hotdoc_cgr
```

#### Creating a basic hotdoc project from the output of gtk-doc's build process.

This next part relies on some arguably fragile parsing of the output of `make` in the gtk-doc folder, assuming an autotools-based project. If the project isn't built with the autotools, or for some reason the parsing script fails, you will need to provide the files detailed at the end of this subsection. In case of a script failure, don't hesitate to open an issue against the [gi-extension](https://github.com/hotdoc/hotdoc_gi_extension/issues).

Additionally, we will need to provide the path to the gir file of the documented library.

The command to run is the following:

```
make clean -C path/to/gtkdoc/folder && make V=1 -C path/to/gtkdoc/folder SHELL="$SHELL -x" 2>&1 | gtk_doc_scan_parser path/to/gir/file
```

Adapted to cgr, this results in:

```
make clean -C ../gcr && make V=1 -C ../gcr SHELL="$SHELL -x" 2>&1 | gtk_doc_scan_parser ../../../Gcr-3.gir
```

Once this was run successfully, we end up with the following:

* A hotdoc.json configuration file, containing the following:
	* A list of C sources (c_sources), which should contain at least one file.
	* A list of include directories (include_directories), which may be empty if the script didn't see any compilation command-line.
	* A list of extra CFLAGS (extra_c_flags), which may be empty for the same reason.
	* The path to a dummy markdown index (index)
	* The path to the gir file (gi_sources)

	In our example, the contents of hotdoc.json look like:

	```
	{
	"c_include_directories": [
		"../../.."
	],
	"c_sources": [
		"../../../gcr/gcr-certificate-request.h", 
		[...],
	],
	"extra_c_flags": [
	        "-Wcast-align",
		[...]
	],
	"gi_sources": [
		"../../../Gcr-3.gir"
	],
	"index": "markdown_files/index.markdown"

	```

* A markdown index in ./markdown_files/index.markdown, containing the following:

	```
	## Welcome to our documentation!

	### [API Reference](gobject-api)
	```

#### Completing the discovered C flags and include directories, and adding pkgconfig packages the lib depends upon

In our example, the previous script successully listed the sources, and discovered some include directories and extra c flags.

We can already check how clang likes our current project with:

```
hotdoc run --dry
```

Not much it seems, a lot of warnings are output in the terminal, we'll start with the most prominent ones:

```
WARNING: [c-extension]: (clang-diagnostic): Clang issue : <Diagnostic severity 3, location <SourceLocation file '/home/meh/devel/gcr/ui/gcr-key-renderer.h', line 19, column 2>, spelling '"Only <gcr/gcr.h> or <gcr/gcr-base.h> can be included directly."'>
```

Classic problem, where gtk-doc didn't care much about preprocessor macros, clang does care, and cgr is a project where only cgr.h is intended for external direct inclusion. A quick look at the sources and at the gir rules shows we need to def and undef a few macros:

```
"extra_c_flags": [
	[...],
	"-DGCR_COMPILATION",
        "-DGCK_API_SUBJECT_TO_CHANGE",
        "-DGCR_API_SUBJECT_TO_CHANGE"
],
```

The next warning we'll look at is:

```
WARNING: [c-extension]: (clang-diagnostic): Clang issue : <Diagnostic severity 4, location <SourceLocation file '/home/meh/devel/gcr/ui/gcr-collection-model.h', line 26, column 10>, spelling "'gtk/gtk.h' file not found">
```

This has to be fixed by adding a pkg_config_packages subsection in the configuration file, and listing "gtk+-3.0" inside it:

```
"pkg_config_packages": [
    "gtk+-3.0"
],
```

Going ahead, we've got a bunch of less obvious issues in various source files. This might be due to these header files not being intended for direct inclusion, and if so there must be a main header file, which might not be listed first in the sources. This is the case in our example, lets's fix that:

```
"c_sources": [
	"../../../gcr/gcr.h",
	[...]
],
```

> In the case of gcr, it didn't seem to fix many issues, but this will speed up clang scanning times and should be done anyway.

The final set of issues is due to missing includes in the header files, as they are not meant for direct inclusion this is not a defect strictly speaking, but it doesn't hurt to "fix" this anyway, as a bonus it also makes other clang-based tools such as [YouCompleteMe](https://github.com/Valloric/YouCompleteMe) happier.

Example issue:

```
WARNING: [c-extension]: (clang-diagnostic): Clang issue : <Diagnostic severity 3, location <SourceLocation file '/home/meh/devel/gcr/gcr/gcr-system-prompt.h', line 82, column 1>, spelling "unknown type name 'GcrPrompt'">
```

and example fix in gcr-system-prompt.h:

```
(dev_env)[meh@meh-host hotdoc_gcr]$ git diff -- ../../../gcr/gcr-system-prompt.h
diff --git a/gcr/gcr-system-prompt.h b/gcr/gcr-system-prompt.h
index 4a6f9ef..0207ab8 100644
--- a/gcr/gcr-system-prompt.h
+++ b/gcr/gcr-system-prompt.h
@@ -27,6 +27,7 @@
 #define __GCR_SYSTEM_PROMPT_H__
 
 #include "gcr-types.h"
+#include "gcr-prompt.h"
 #include "gcr-secret-exchange.h"
 
 #include <glib-object.h>
(dev_env)[meh@meh-host hotdoc_gcr]$
```

The rest of the warnings are fixed in a similar fashion, until none is left.

#### Finalizing the port.

With this done, the last thing to do is to run the actual porting script, `gtk_doc_porter`.

> This script will modify the hotdoc.json file, and the markdown_files directory contents. It will also make modifications in the source code comments, by removing the SECTION comments to place them in standalone markdown files, except for the SECTION comments which really described classes, these are renamed to ClassName::ClassName, which is the hotdoc way of specifying that a comment applies to a class. This is well-tested and should not fail, but like all automatic source code mofifications, it's very recommended to give the diff a good look before commiting it. If you have made changes to the sources in the previous step, it might be a good idea to commit it before running that script.

First save the hotdoc.json file just in case:

```
cp hotdoc.json backup.json
```

Then run:

```
gtk_doc_porter --section-file path/to/section/file --docbook-index path/to/docbook/root --conf-file hotdoc.json
```

> If the library did not have a sections file under version control, gtk-doc was generating one on-the-fly for it, and you don't need to pass one here. You can check this with `git ls-files path/to/sections.txt`, if this doesn't output anything then the sections file was not documented.

In our case (cgr distributes its sections.txt), this translates to:

```
gtk_doc_porter --section-file ../gcr/gcr-sections.txt --docbook-index ../gcr/gcr-docs.sgml --conf-file hotdoc.json
```

If all went well, you can now build the new documentation with:

```
hotdoc run
```

and checkout the results by opening `built_doc/html/index.html` in a web browser:

```
xdg-open built_doc/html/index.html
```

#### Git integration

You may want to add the following to your .gitignore files, for example if the project uses gitignore files in each subfolder, you will put the following in the hotdoc folder:

```
built_doc
hotdoc-private
```

If the project uses a single, toplevel .gitignore file, prefix this with the path to the hotdoc folder, this is the case in gcr so we'll update the toplevel .gitignore as such:

```
(dev_env)[meh@meh-host gcr]$ git diff -- .gitignore
diff --git a/.gitignore b/.gitignore
index ce969fc..506bd5a 100644
--- a/.gitignore
+++ b/.gitignore
@@ -74,7 +74,9 @@ stamp-*
 /docs/reference/*/tmpl
 /docs/reference/*/version.xml
 /docs/reference/*/version.xml
-/docs/reference/*/
+
+docs/reference/hotdoc_gcr/hotdoc-private
+docs/reference/hotdoc_gcr/built_doc
 
 /egg/asn1-def-*.c
 /egg/tests/asn1-def-*.c
(dev_env)[meh@meh-host gcr]$
```

The files to track are the following:

* The hotdoc.json file
* All files in the markdown_files folder

#### Autotools build files

Might be a good idea to finalize this before documenting it :)

#### Result for gcr

You can check the two commits (there will be a third one for autotools integration) [here](https://github.com/hotdoc/hotdoc_gcr/commits/port_to_hotdoc).

You can browse the resulting documentation [there](https://people.collabora.com/~meh/gcr_hotdoc/html/python/gcr-certificate.html).
