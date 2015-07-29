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
        clang_options = os.getenv("CLANG_OPTIONS")

        if clang_options:
            clang_options = clang_options.split(' ')
        index = clang.cindex.Index.create()
        flags = clang.cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES |\
                clang.cindex.TranslationUnit.PARSE_INCOMPLETE |\
                clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD

        self.filenames = [os.path.abspath(filename) for filename in filenames]

        args = ["-I/usr/lib/clang/3.5.0/include/"]
        args.extend (clang_options)

        self.symbols = {}
        self.external_symbols = {}
        self.comments = []

        self.parsed = set({})

        n = datetime.now()
        for filename in self.filenames:
            self.comments.extend(get_comments(filename))

            if os.path.abspath(filename) in self.parsed:
                continue

            if not filename.endswith ("c"):
                tu = index.parse(filename, args=args, options=flags)
                for diag in tu.diagnostics:
                    print diag

                cursor = tu.cursor
                for c in cursor.get_children ():
                    filename = str(c.location.file)
                    self.parsed.add (os.path.abspath(filename))
                    if os.path.abspath(filename) in self.filenames:
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

    def lookup_ast_node (self, name):
        return self.symbols.get(name) or self.external_symbols.get(name)

    def lookup_underlying_type (self, name):
        ast_node = self.lookup_ast_node (name)
        if not ast_node:
            return None

        while ast_node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            t = ast_node.underlying_typedef_type
            ast_node = t.get_declaration()
        return ast_node.kind

if __name__=="__main__": 
    css = ClangScanner ([sys.argv[1]])
    print css.comments
