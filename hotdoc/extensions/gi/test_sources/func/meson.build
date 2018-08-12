project('function', 'c', version : '1.0')

gnome = import('gnome')
files_ = ['function.c', 'function.h']

gobj = dependency('gobject-2.0')
obj = dependency('obj', fallback: ['obj', 'dep'])
funclib = shared_library('funclib', files_, dependencies: obj)

gir = gnome.generate_gir(funclib,
      sources : files_,
      namespace : 'Func',
      nsversion : '1.0',
      identifier_prefix : 'Func',
      symbol_prefix : 'func',
      install : true,
)
