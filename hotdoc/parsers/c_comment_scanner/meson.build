flex = find_program('flex', native: true)

scanner_c = custom_target(
    input: 'scanner.l',
    output: 'scanner.c',
    command: [flex, '-o', '@OUTPUT@', '@INPUT@'],
)

py.extension_module('c_comment_scanner',
    'scannermodule.c',
    scanner_c,
    install: true,
    c_args: ['-D_POSIX_C_SOURCE=1', '-D_XOPEN_SOURCE=600'],
    subdir: 'hotdoc/parsers/c_comment_scanner',
)
