# GI-DOC

## Step by Step porting of [gstreamer](http://gstreamer.freedesktop.org/) from gtk-doc to gi-doc.

> You will absolutely need the latest gobject-introspection from git to follow this tutorial

### Translating the documentation.

The [new syntax](syntax_summary.markdown) parsed by gi-doc differs
from the [old gtk-doc syntax](https://wiki.gnome.org/Projects/GTK%2B/DocumentationSyntax/Markdown).

This is not the place to explain this change though, all you need to know is that the comment blocks
will need to be ported.

Fortunately a script is available for this, `gtkdoc_to_gidoc.py`.

We will need to provide it with a list of files to translate (the `--filenames` switch), and maybe
some other options.

First, let's find out what files I'll want to translate. As gstreamer already builds a gir file,
a neat trick we can use is this one, from gstreamer's root directory:

```shell
cd gst
mv Gst-1.0.gir original_gir.gir
make -n Gst-1.0.gir
```

This gives us the following output:

```
echo "  GEN     " Gst-1.0.gir;GST_PLUGIN_SYSTEM_PATH_1_0="" GST_PLUGIN_PATH_1_0="" GST_REGISTRY_UPDATE=no GI_SCANNER_DISABLE_CACHE=yes\
  /usr/local/bin/g-ir-scanner -v --namespace Gst \
  --nsversion=1.0 \
  --warn-all \
  -I.. \
  -I.. \
  -DIN_GOBJECT_INTROSPECTION=1 \
  --c-include='gst/gst.h' \
  --library=libgstreamer-1.0.la \
  --include=GLib-2.0 \
  --include=GObject-2.0 \
  --include=GModule-2.0 \
  --libtool="/bin/sh ../libtool" \
  --pkg glib-2.0 \
  --pkg gobject-2.0 \
  --pkg gmodule-no-export-2.0 \
  --pkg-export gstreamer-1.0 \
  --add-init-section="extern void gst_init(gint*,gchar**); gst_init(NULL,NULL);" \
  --output Gst-1.0.gir \
  ./gst.h ./glib-compat.h ./gstobject.h ./gstallocator.h ./gstbin.h ./gstbuffer.h ./gstbufferlist.h ./gstbufferpool.h ./gstbus.h ./gstcaps.h ./gstcapsfeatures.h ./gstchildproxy.h ./gstclock.h ./gstcompat.h ./gstcontext.h ./gstcontrolbinding.h ./gstcontrolsource.h ./gstdatetime.h ./gstdebugutils.h ./gstelement.h ./gstelementmetadata.h ./gstdevice.h ./gstdeviceprovider.h ./gstdeviceproviderfactory.h ./gstelementfactory.h ./gsterror.h ./gstevent.h ./gstformat.h ./gstghostpad.h ./gstdevicemonitor.h ./gstinfo.h ./gstiterator.h ./gstatomicqueue.h ./gstmacros.h ./gstmessage.h ./gstmeta.h ./gstmemory.h ./gstminiobject.h ./gstpad.h ./gstpadtemplate.h ./gstparamspecs.h ./gstpipeline.h ./gstplugin.h ./gstpluginfeature.h ./gstpoll.h ./gstpreset.h ./gstprotection.h ./gstquery.h ./gstsample.h ./gstsegment.h ./gststructure.h ./gstsystemclock.h ./gsttaglist.h ./gsttagsetter.h ./gsttask.h ./gsttaskpool.h ./gsttoc.h ./gsttocsetter.h ./gsttypefind.h ./gsttypefindfactory.h ./gsturi.h ./gstutils.h ./gstvalue.h ./gstregistry.h ./gstparse.h ./math-compat.h ./gstenumtypes.h ./gstversion.h \
  ./gst.c ./gstobject.c ./gstallocator.c ./gstbin.c ./gstbuffer.c ./gstbufferlist.c ./gstbufferpool.c ./gstbus.c ./gstcaps.c ./gstcapsfeatures.c ./gstchildproxy.c ./gstclock.c ./gstclock-linreg.c ./gstcontext.c ./gstcontrolbinding.c ./gstcontrolsource.c ./gstdatetime.c ./gstdebugutils.c ./gstdevice.c ./gstdevicemonitor.c ./gstdeviceprovider.c ./gstdeviceproviderfactory.c ./gstelement.c ./gstelementfactory.c ./gsterror.c ./gstevent.c ./gstformat.c ./gstghostpad.c ./gstinfo.c ./gstiterator.c ./gstatomicqueue.c ./gstmessage.c ./gstmeta.c ./gstmemory.c ./gstminiobject.c ./gstpad.c ./gstpadtemplate.c ./gstparamspecs.c ./gstpipeline.c ./gstplugin.c ./gstpluginfeature.c ./gstpluginloader.c ./gstpoll.c ./gstpreset.c ./gstprotection.c ./gstquark.c ./gstquery.c ./gstregistry.c ./gstregistrychunks.c ./gstsample.c ./gstsegment.c ./gststructure.c ./gstsystemclock.c ./gsttaglist.c ./gsttagsetter.c ./gsttask.c ./gsttaskpool.c ./gsttoc.c ./gsttocsetter.c ./gsttrace.c ./gsttypefind.c ./gsttypefindfactory.c ./gsturi.c ./gstutils.c ./gstvalue.c ./gstparse.c ./gstregistrybinary.c ./gstenumtypes.c
```

Wonderful! We now have our list of filenames, let's try with that:

```shell
/home/meh/devel/better_doctool/gtkdoc_to_gidoc.py --filenames ./gst.h ./glib-compat.h ./gstobject.h ./gstallocator.h ./gstbin.h ./gstbuffer.h ./gstbufferlist.h ./gstbufferpool.h ./gstbus.h ./gstcaps.h ./gstcapsfeatures.h ./gstchildproxy.h ./gstclock.h ./gstcompat.h ./gstcontext.h ./gstcontrolbinding.h ./gstcontrolsource.h ./gstdatetime.h ./gstdebugutils.h ./gstelement.h ./gstelementmetadata.h ./gstdevice.h ./gstdeviceprovider.h ./gstdeviceproviderfactory.h ./gstelementfactory.h ./gsterror.h ./gstevent.h ./gstformat.h ./gstghostpad.h ./gstdevicemonitor.h ./gstinfo.h ./gstiterator.h ./gstatomicqueue.h ./gstmacros.h ./gstmessage.h ./gstmeta.h ./gstmemory.h ./gstminiobject.h ./gstpad.h ./gstpadtemplate.h ./gstparamspecs.h ./gstpipeline.h ./gstplugin.h ./gstpluginfeature.h ./gstpoll.h ./gstpreset.h ./gstprotection.h ./gstquery.h ./gstsample.h ./gstsegment.h ./gststructure.h ./gstsystemclock.h ./gsttaglist.h ./gsttagsetter.h ./gsttask.h ./gsttaskpool.h ./gsttoc.h ./gsttocsetter.h ./gsttypefind.h ./gsttypefindfactory.h ./gsturi.h ./gstutils.h ./gstvalue.h ./gstregistry.h ./gstparse.h ./math-compat.h ./gstenumtypes.h ./gstversion.h ./gst.c ./gstobject.c ./gstallocator.c ./gstbin.c ./gstbuffer.c ./gstbufferlist.c ./gstbufferpool.c ./gstbus.c ./gstcaps.c ./gstcapsfeatures.c ./gstchildproxy.c ./gstclock.c ./gstclock-linreg.c ./gstcontext.c ./gstcontrolbinding.c ./gstcontrolsource.c ./gstdatetime.c ./gstdebugutils.c ./gstdevice.c ./gstdevicemonitor.c ./gstdeviceprovider.c ./gstdeviceproviderfactory.c ./gstelement.c ./gstelementfactory.c ./gsterror.c ./gstevent.c ./gstformat.c ./gstghostpad.c ./gstinfo.c ./gstiterator.c ./gstatomicqueue.c ./gstmessage.c ./gstmeta.c ./gstmemory.c ./gstminiobject.c ./gstpad.c ./gstpadtemplate.c ./gstparamspecs.c ./gstpipeline.c ./gstplugin.c ./gstpluginfeature.c ./gstpluginloader.c ./gstpoll.c ./gstpreset.c ./gstprotection.c ./gstquark.c ./gstquery.c ./gstregistry.c ./gstregistrychunks.c ./gstsample.c ./gstsegment.c ./gststructure.c ./gstsystemclock.c ./gsttaglist.c ./gsttagsetter.c ./gsttask.c ./gsttaskpool.c ./gsttoc.c ./gsttocsetter.c ./gsttrace.c ./gsttypefind.c ./gsttypefindfactory.c ./gsturi.c ./gstutils.c ./gstvalue.c ./gstparse.c ./gstregistrybinary.c ./gstenumtypes.c
```

Output:

```
In file included from <stdin>:4:0:
/home/meh/pitivi-git/gstreamer/gst/gst.h:27:18: fatal error: glib.h: No such file or directory
compilation terminated.
Error while processing the source.
```

Grmph. OK so we obviously need to let the tool know where the glib headers live, and certainly the gobject ones too.
As pkg-config can tell us that, let's just use the --packages switch:

```shell
/home/meh/devel/better_doctool/gtkdoc_to_gidoc.py --filenames ./gst.h [...] --packages gobject-2.0
```

Output:

```
In file included from <stdin>:4:0:
/home/meh/pitivi-git/gstreamer/gst/gst.h:29:29: fatal error: gst/glib-compat.h: No such file or directory
compilation terminated.
Error while processing the source.
```

OK well we went past that first error, good :)

That second one is a bit trickier, as I can't assume a pkg-config file even exists.
Let's just use the -I flag for that:

> Note: the tool only accepts one -I parameter, if you have various paths to add just pass them all at the same
> time (-I my/first/path my/second/path)

```shell
/home/meh/devel/better_doctool/gtkdoc_to_gidoc.py --filenames ./gst.h [...] --packages gobject-2.0 -I ..
```

Output:

```
Wow lots of stuff !!
```

This time it worked ! And a crazy load of stuff got printed to the terminal too by the way =D

That is because the tool won't touch the sources unless explicitly required to, and we can take
advantage of that to check that the output looks correct too. One of the last things I see is
`Returns: (transfer full): a [GstBus]()`, which doesn't strike me as blatantly incorrect, so let's
just go ahead and pass the --inplace flag to the tool:

Full command:

```shell
/home/meh/devel/better_doctool/gtkdoc_to_gidoc.py --filenames ./gst.h ./glib-compat.h ./gstobject.h ./gstallocator.h ./gstbin.h ./gstbuffer.h ./gstbufferlist.h ./gstbufferpool.h ./gstbus.h ./gstcaps.h ./gstcapsfeatures.h ./gstchildproxy.h ./gstclock.h ./gstcompat.h ./gstcontext.h ./gstcontrolbinding.h ./gstcontrolsource.h ./gstdatetime.h ./gstdebugutils.h ./gstelement.h ./gstelementmetadata.h ./gstdevice.h ./gstdeviceprovider.h ./gstdeviceproviderfactory.h ./gstelementfactory.h ./gsterror.h ./gstevent.h ./gstformat.h ./gstghostpad.h ./gstdevicemonitor.h ./gstinfo.h ./gstiterator.h ./gstatomicqueue.h ./gstmacros.h ./gstmessage.h ./gstmeta.h ./gstmemory.h ./gstminiobject.h ./gstpad.h ./gstpadtemplate.h ./gstparamspecs.h ./gstpipeline.h ./gstplugin.h ./gstpluginfeature.h ./gstpoll.h ./gstpreset.h ./gstprotection.h ./gstquery.h ./gstsample.h ./gstsegment.h ./gststructure.h ./gstsystemclock.h ./gsttaglist.h ./gsttagsetter.h ./gsttask.h ./gsttaskpool.h ./gsttoc.h ./gsttocsetter.h ./gsttypefind.h ./gsttypefindfactory.h ./gsturi.h ./gstutils.h ./gstvalue.h ./gstregistry.h ./gstparse.h ./math-compat.h ./gstenumtypes.h ./gstversion.h ./gst.c ./gstobject.c ./gstallocator.c ./gstbin.c ./gstbuffer.c ./gstbufferlist.c ./gstbufferpool.c ./gstbus.c ./gstcaps.c ./gstcapsfeatures.c ./gstchildproxy.c ./gstclock.c ./gstclock-linreg.c ./gstcontext.c ./gstcontrolbinding.c ./gstcontrolsource.c ./gstdatetime.c ./gstdebugutils.c ./gstdevice.c ./gstdevicemonitor.c ./gstdeviceprovider.c ./gstdeviceproviderfactory.c ./gstelement.c ./gstelementfactory.c ./gsterror.c ./gstevent.c ./gstformat.c ./gstghostpad.c ./gstinfo.c ./gstiterator.c ./gstatomicqueue.c ./gstmessage.c ./gstmeta.c ./gstmemory.c ./gstminiobject.c ./gstpad.c ./gstpadtemplate.c ./gstparamspecs.c ./gstpipeline.c ./gstplugin.c ./gstpluginfeature.c ./gstpluginloader.c ./gstpoll.c ./gstpreset.c ./gstprotection.c ./gstquark.c ./gstquery.c ./gstregistry.c ./gstregistrychunks.c ./gstsample.c ./gstsegment.c ./gststructure.c ./gstsystemclock.c ./gsttaglist.c ./gsttagsetter.c ./gsttask.c ./gsttaskpool.c ./gsttoc.c ./gsttocsetter.c ./gsttrace.c ./gsttypefind.c ./gsttypefindfactory.c ./gsturi.c ./gstutils.c ./gstvalue.c ./gstparse.c ./gstregistrybinary.c ./gstenumtypes.c --packages gobject-2.0 -I .. --inplace
```

Output:

```
sources scanned
Translating /home/meh/pitivi-git/gstreamer/gst/gstallocator.h
Translating /home/meh/pitivi-git/gstreamer/gst/gstiterator.c
Translating /home/meh/pitivi-git/gstreamer/gst/gstvalue.c
[...]
```

Woot! Looking good now :)

Compiling again with `make` works as expected, great!

I will just commit and leave it as is, you should obviously exercise caution and make sure the job was well done,
a relatively safe way to do so  is to check if the gir coverage has changed in any way:

```shell
grep "<method name=" original_gir.gir > tmp1.txt && grep "<method name=" Gst-1.0.gir > tmp2.txt && diff tmp1.txt tmp2.txt && rm tmp1.txt tmp2.txt
```

No output ? Cool, let's go ahead.

### Translating the sgml files.

Some words of warning: we will now translate gstreamer's docbook files to markdown. This step wouldn't be strictly necessary if pandoc's
coverage of docbook was complete, as gi-doc can handle all sorts of formats as an input.

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

## Building doc with gi-doc

```shell
mkdir new_doc
/home/meh/devel/better_doctool/doctool.py ../../gst/Gst-1.0.gir -o new_doc -i markdown_files/index.markdown
```
