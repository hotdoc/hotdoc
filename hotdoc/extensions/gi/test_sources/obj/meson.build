project('obj', 'c', version : '1.0')

gnome = import('gnome')
files_ = ['obj.c', 'obj.h']
gobj = dependency('gobject-2.0')
objectlib = shared_library('objectlib', files_, dependencies: [gobj])

gir = gnome.generate_gir(objectlib,
      sources : files_,
      nsversion : '1.0',
      namespace : 'Obj',
      identifier_prefix : 'Obj',
      symbol_prefix : 'obj',
      includes : ['GLib-2.0', 'GObject-2.0'],
      install : true,
)

dep = declare_dependency(link_with: objectlib, dependencies : [gobj],
        include_directories: include_directories('.'))
