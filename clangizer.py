#!/usr/bin/env python

import os
import sys
from datetime import datetime, timedelta
import clang.cindex

from lol import show_ast
from scanner.scanner import get_comments


def ast_node_is_function_pointer (ast_node):
    if ast_node.kind == clang.cindex.TypeKind.POINTER and \
            ast_node.get_pointee().get_result().kind != \
            clang.cindex.TypeKind.INVALID:
        return True
    return False


class ClangScanner(object):
    def __init__(self, filenames):
        index = clang.cindex.Index.create()
        flags = clang.cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES |\
                clang.cindex.TranslationUnit.PARSE_INCOMPLETE |\
                clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD

        self.filenames = [os.path.abspath(filename) for filename in filenames]

        args=["-I/home/meh/pitivi-git/gstreamer/gst",
              "-I/home/meh/pitivi-git/gstreamer/",
              "-isystem /usr/include/glib-2.0",
              "-isystem /usr/lib64/glib-2.0/include",
              "-I../libs",
              "-I..",
              "-pthread",
              "-I/usr/include/glib-2.0",
              "-I/usr/lib64/glib-2.0/include",
              "-I/usr/lib/clang/3.5.0/include/",
              "-D_GNU_SOURCE",
              "-DGST_EXPORTS",
              '-DGST_API_VERSION=\""1.0"\"',
              "-DGST_DISABLE_DEPRECATED",
              "-DHAVE_CONFIG_H",
              ]

        self.symbols = {}
        self.external_symbols = {}
        self.comments = []

        self.parsed = set({})

        n = datetime.now()
        for filename in self.filenames:
            self.comments.extend(get_comments(filename))

            if filename in self.parsed:
                continue

            if not filename.endswith ("c"):
                tu = index.parse(filename, args=args, options=flags)

                cursor = tu.cursor
                for c in cursor.get_children ():
                    filename = str(c.location.file)
                    self.parsed.add (filename)
                    if filename in self.filenames:
                        self.find_internal_symbols(c)
                    else:
                        self.find_external_symbols(c)

        print "Source parsing done !", datetime.now() - n

    def find_internal_symbols(self, node):
        if node.kind in [clang.cindex.CursorKind.FUNCTION_DECL,
                         clang.cindex.CursorKind.TYPEDEF_DECL,
                         clang.cindex.CursorKind.MACRO_DEFINITION]:
            self.symbols[node.spelling] = node

        for c in node.get_children():
            self.find_internal_symbols(c)

    def find_external_symbols(self, node):
        if node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            self.external_symbols[node.spelling] = node

if __name__=="__main__": 
    css = ClangScanner ([sys.argv[1]])
    print css.comments
