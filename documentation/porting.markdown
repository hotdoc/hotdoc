## Step by Step porting of [gstreamer](http://gstreamer.freedesktop.org/) from gtk-doc to hotdoc.

### Translating the sgml files.

Some words of warning: we will now translate gstreamer's docbook files to markdown. This step wouldn't be strictly necessary if pandoc's
coverage of docbook was complete, as hotdoc can handle all sorts of formats as an input.

As these limitations exist, I've taken the pragmatic approach of parsing the top-level sgml file with a custom made script, and use pandoc
to do the heavy lifting of parsing the various xincluded files. There will however be some contents lost in translation, and some parts
not laid out as they were before. The work of fixing this shouldn't be overwhelming though, but if someone (:hint:) wanted to improve
pandoc's docbook reader, all the better !

This custom made script is far from flawless, and really quick and dirty as it's just there to help with the transition. I initially
developed it against gtk, and had to fix two bugs I found while writing this documentation. Don't hesitate to open it and fix it,
and marvel at the overall laziness of it ;)

With that said, let's get back to work.

The new design incorporates the old "sections" file as just another markdown file. We will use the old
sections file when translating the docbook files, but we will need to do a tiny bit of processing on it first.

From gstreamer's root directory:

```shell
cd docs/gst
/home/meh/devel/better_doctool/translate_sections.sh gstreamer-sections.txt tmpsections.txt
```

This is a one-liner shell script, not much to say about it.

Now that we've got our translated sections, we will want to generate our new markdown files. This is done with:

```shell
mkdir markdown_files
/home/meh/devel/better_doctool/sgml_to_sections.py gstreamer-docs.sgml tmpsections.txt markdown_files
```

If that worked, you can open markdown_files/index.markdown and dig down the rabbit hole to see the
overall structure. You can also safely remove tmpsections.txt

If it didn't, please open an issue with a link to the project you are porting (or improve pandoc's docbook reader :)

The porting is now done, head to the next chapter to learn how to build your new doc, and figure out how to
fix the artefacts introduced by the translation.

## Building doc with hotdoc

```shell
mkdir new_doc
hotdoc ../../gst/Gst-1.0.gir -o new_doc -i markdown_files/index.markdown
```
