flex = find_program('flex', 'win_flex', required: get_option('c-extension'))

if not flex.found()
    message('Not building C and GI extensions as `flex` was not found')
    subdir_done()
endif

parser = custom_target('parselex',
  input : 'scanner.l',
  output : ['scanner.c'],
  command : [flex, '-o', '@OUTPUT0@', '@INPUT@']
)

modules += [python.extension_module('c_comment_scanner', 'scannermodule.c', parser,
    dependencies: python.dependency(),
    subdir: 'hotdoc/parsers/c_comment_scanner',
    install: true)]

foreach f: ['__init__.py',]
    python.install_sources(f, pure: false, subdir: 'hotdoc/parsers/c_comment_scanner')
    to_symlink += [[meson.current_source_dir() / f, meson.current_build_dir() / f]]
endforeach