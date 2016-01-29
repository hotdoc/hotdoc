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


def add_md_includes(contents, source_file, include_paths, lineno=0):
    """
    Add includes from the @contents markdown and return the new patched content
    Args:
        contents: str, a markdown string
        source_file: str, the file from which @contents comes from
        include_paths: list, The list of include paths from the configuration
        lineo: int, The line number from which the content comes from in
            source_file
    """
    inclusions = set(re.findall('{{(.+?)}}', contents))
    for inclusion in inclusions:
        include_filename = inclusion.strip()
        include_path = __find_included_file(include_filename, include_paths)
        try:
            included_content = include_signal(include_path.strip())[0]
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
