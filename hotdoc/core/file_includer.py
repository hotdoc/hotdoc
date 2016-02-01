"""
The markdown file including system
"""
import re
import os

from hotdoc.utils.simple_signals import Signal

# pylint: disable=invalid-name
include_signal = Signal()


def __find_included_file(filename, include_paths):
    if os.path.isabs(filename):
        return filename

    for include_path in include_paths:
        fpath = os.path.join(include_path, filename)
        if os.path.exists(fpath):
            return fpath

    return filename


def __parse_include(include):
    include = include.strip()
    line_ranges_str = re.findall(r'\[(.+?):(.+?)\]', include)
    line_ranges = []
    for s, e in line_ranges_str:
        line_ranges.append((int(s), int(e)))

    include = re.sub(r'\[(.+?):(.+?)\]', "", include)
    try:
        symbol = re.findall(r'#(.+?)$', include)[0]
    except IndexError:
        symbol = None

    include_filename = re.sub(r'#.*$', "", include)

    return (include_filename, line_ranges, symbol)


def add_md_includes(contents, source_file, include_paths=None, lineno=0):
    """
    Add includes from the @contents markdown and return the new patched content
    Args:
        contents: str, a markdown string
        source_file: str, the file from which @contents comes from
        include_paths: list, The list of include paths from the configuration
        lineo: int, The line number from which the content comes from in
            source_file
    """

    if include_paths is None:
        return contents

    inclusions = set(re.findall('{{(.+?)}}', contents))
    for inclusion in inclusions:
        include_filename, line_ranges, symbol = __parse_include(inclusion)
        include_path = __find_included_file(include_filename, include_paths)
        try:
            for c in include_signal(include_path.strip(), line_ranges, symbol):
                if c is not None:
                    included_content = c
                    break

            nincluded_content = included_content
            including = True
            while including:
                # Recurse in the included content
                nincluded_content = add_md_includes(
                    nincluded_content, include_path, include_paths, lineno)
                including = (nincluded_content != included_content)
                included_content = nincluded_content
        except IOError as e:
            raise type(e)("Could not include '%s' in %s - include line: '%s'"
                          " (%s)" % (include_path, source_file,
                                     lineno, e.message))

        contents = contents.replace('{{' + inclusion + '}}', included_content)

    return contents
