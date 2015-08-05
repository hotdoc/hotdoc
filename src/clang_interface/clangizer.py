#!/usr/bin/env python

import os
import sys
from datetime import datetime, timedelta
import clang.cindex
from clang.cindex import *

from utils.loggable import Loggable, progress_bar
from lexer_parsers.gtkdoc_parser.gtkdoc_parser import parse_comment_blocks
from lexer_parsers.c_comment_scanner.c_comment_scanner import get_comments
from ctypes import *
from fnmatch import fnmatch

def ast_node_is_function_pointer (ast_node):
    if ast_node.kind == clang.cindex.TypeKind.POINTER and \
            ast_node.get_pointee().get_result().kind != \
            clang.cindex.TypeKind.INVALID:
        return True
    return False


class ClangScanner(Loggable):
    def __init__(self, filenames, full_scan=False, full_scan_patterns=['*.h']):
        Loggable.__init__(self)
        clang_options = os.getenv("CLANG_OPTIONS")

        self.full_scan = full_scan
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
        self.token_groups = []
        self.__total_files = len (self.filenames)
        self.__total_files_parsed = 0

        if progress_bar is not None:
            progress_bar.set_header("Parsing sources (1 / 2)")
            progress_bar.clear()
            self.__update_progress()

        self.parsed = set({})

        n = datetime.now()
        self.new_comments = {}
        for filename in self.filenames:
            if not full_scan:
                with open (filename, 'r') as f:
                    #print "Doing filename", filename
                    for block in parse_comment_blocks (f.read()):
                        self.new_comments[block.name] = block

            if os.path.abspath(filename) in self.parsed:
                continue

            do_full_scan = any(fnmatch(filename, p) for p in full_scan_patterns)
            if do_full_scan:
                tu = index.parse(filename, args=args, options=flags)
                self.__parse_file (filename, tu)
                for include in tu.get_includes():
                    self.__parse_file (os.path.abspath(str(include.source)), tu)
            else:
                self.__total_files_parsed += 1
                self.__update_progress ()

        self.info ("Source parsing done %s" % str(datetime.now() - n))
        self.info ("%d internal symbols found" % len (self.symbols))
        self.info ("%d external symbols found" % len (self.external_symbols))
        self.info ("%d comments found" % len (self.new_comments))


    def __update_progress (self):
        if progress_bar is None:
            return
        percent = float (self.__total_files_parsed) / float (self.__total_files)
        progress_bar.update (percent, "%d / %d" %
                (self.__total_files_parsed, self.__total_files)) 

    def __parse_file (self, filename, tu):
        if filename in self.parsed:
            return

        self.parsed.add (os.path.abspath(filename))
        start = tu.get_location (filename, 0)
        end = tu.get_location (filename, os.path.getsize(filename))
        extent = clang.cindex.SourceRange.from_locations (start, end)
        cursors = self.__get_cursors(tu, extent)
        if filename in self.filenames:
            self.__total_files_parsed += 1
            self.__update_progress ()
            self.find_internal_symbols (cursors, tu)
        else:
            self.find_external_symbols (cursors, tu)

    # That's the fastest way of obtaining our ast nodes for a given filename
    def __get_cursors (self, tu, extent):
        tokens_memory = POINTER(Token)()
        tokens_count = c_uint()

        clang.cindex.conf.lib.clang_tokenize(tu, extent, byref(tokens_memory),
                byref(tokens_count))

        count = int(tokens_count.value)

        if count < 1:
            return

        self.token_groups.append(clang.cindex.TokenGroup(tu, tokens_memory, tokens_count))
        cursors = (Cursor * count)()
        clang.cindex.conf.lib.clang_annotateTokens (tu, tokens_memory, tokens_count,
                cursors)

        return cursors

    def find_internal_symbols(self, nodes, tu):
        for node in nodes:
            if node.kind in [clang.cindex.CursorKind.FUNCTION_DECL,
                            clang.cindex.CursorKind.TYPEDEF_DECL,
                            clang.cindex.CursorKind.MACRO_DEFINITION]:
                if self.full_scan and not node.raw_comment:
                    self.debug ("Discarding symbol %s at location %s as it has no doc" %
                            (node.spelling, str(node.location)))
                    continue

                self.symbols[node.spelling] = node
                self.debug ("Found internal symbol [%s] of kind %s at location %s" %
                        (node.spelling, str(node.kind), str (node.location)))
                node._tu = tu

    def find_external_symbols(self, nodes, tu):
        for node in nodes:
            if node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                self.external_symbols[node.spelling] = node
                self.debug ("Found external symbol %s" % node.spelling)
                node._tu = tu

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
