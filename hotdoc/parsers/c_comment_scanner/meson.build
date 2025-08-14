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
    subdir: 'hotdoc/parsers/c_comment_scanner',
)