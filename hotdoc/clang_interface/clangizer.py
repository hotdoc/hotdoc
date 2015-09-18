#!/usr/bin/env python

import os
import sys
import linecache
from datetime import datetime, timedelta
import clang.cindex
from ctypes import *
from fnmatch import fnmatch

from hotdoc.utils.loggable import Loggable, progress_bar
from hotdoc.lexer_parsers.c_comment_scanner.c_comment_scanner import get_comments

def ast_node_is_function_pointer (ast_node):
    if ast_node.kind == clang.cindex.TypeKind.POINTER and \
            ast_node.get_pointee().get_result().kind != \
            clang.cindex.TypeKind.INVALID:
        return True
    return False


class ClangScanner(Loggable):
    def __init__(self, config, options):
        Loggable.__init__(self)

        self.__config = config

        if options:
            options = options[0].split(' ')

        index = clang.cindex.Index.create()
        flags = clang.cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES |\
                clang.cindex.TranslationUnit.PARSE_INCOMPLETE |\
                clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD

        self.filenames = [os.path.abspath(filename) for filename in
                config.dependency_tree.stale_sources]

        args = ["-I/usr/lib/clang/3.5.0/include/", "-Wno-attributes"]
        args.extend (options)

        self.symbols = {}
        self.new_symbols = {}

        self.external_symbols = {}
        self.comments = {}
        self.token_groups = []
        self.tus = []
        self.__total_files = len (self.filenames)
        self.__total_files_parsed = 0

        self.__progress_bar = progress_bar.get_progress_bar ()
        if self.__progress_bar is not None:
            self.__progress_bar.set_header("Parsing sources (1 / 2)")
            self.__progress_bar.clear()
            self.__update_progress()

        self.parsed = set({})

        n = datetime.now()

        if not self.__config.full_scan:
            for filename in self.filenames:
                with open (filename, 'r') as f:
                    cs = get_comments (filename)
                    for c in cs:
                        block = self.__config.raw_comment_parser.parse_comment(c[0], c[1], c[2])
                        self.comments[block.name] = block

        for filename in self.filenames:
            if os.path.abspath(filename) in self.parsed:
                continue

            do_full_scan = any(fnmatch(filename, p) for p in self.__config.full_scan_patterns)
            if do_full_scan:
                tu = index.parse(filename, args=args, options=flags)
                self.tus.append (tu)
                for diag in tu.diagnostics:
                    if diag.severity <= 2 and str(diag.location.file) not in self.filenames:
                        self.warning ("Clang issue : %s" % str (diag))
                    else:
                        self.error ("Clang issue : %s" % str (diag))
                self.__parse_file (filename, tu)
                for include in tu.get_includes():
                    self.__parse_file (os.path.abspath(str(include.source)), tu)
            else:
                self.__total_files_parsed += 1
                self.__update_progress ()

        self.info ("Source parsing done %s" % str(datetime.now() - n))
        self.info ("%d internal symbols found" % len (self.symbols))
        self.info ("%d external symbols found" % len (self.external_symbols))
        self.info ("%d comments found" % len (self.comments))

        print self.new_symbols

    def __update_progress (self):
        if self.__progress_bar is None:
            return

        if self.__total_files == 0:
            return

        percent = float (self.__total_files_parsed) / float (self.__total_files)
        self.__progress_bar.update (percent, "%d / %d" %
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
        tokens_memory = POINTER(clang.cindex.Token)()
        tokens_count = c_uint()

        clang.cindex.conf.lib.clang_tokenize(tu, extent, byref(tokens_memory),
                byref(tokens_count))

        count = int(tokens_count.value)

        if count < 1:
            return

        self.token_groups.append(clang.cindex.TokenGroup(tu, tokens_memory, tokens_count))
        cursors = (clang.cindex.Cursor * count)()
        clang.cindex.conf.lib.clang_annotateTokens (tu, tokens_memory, tokens_count,
                cursors)

        return cursors

    def find_internal_symbols(self, nodes, tu):
        for node in nodes:
            node._tu = tu
            if node.kind in [clang.cindex.CursorKind.FUNCTION_DECL,
                            clang.cindex.CursorKind.TYPEDEF_DECL,
                            clang.cindex.CursorKind.MACRO_DEFINITION,
                            clang.cindex.CursorKind.VAR_DECL]:
                if self.__config.full_scan:
                    if not node.raw_comment:
                        self.debug ("Discarding symbol %s at location %s as it has no doc" %
                                (node.spelling, str(node.location)))
                        continue

                    self.comments[node.spelling] = \
                        self.__config.raw_comment_parser.parse_comment \
                                (node.raw_comment, str(node.location.file), 0)

                self.symbols[node.spelling] = node
                self.debug ("Found internal symbol [%s] of kind %s at location %s" %
                        (node.spelling, str(node.kind), str (node.location)))

            if node.spelling in self.new_symbols:
                continue

            sym = None
            if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
                sym = self.__create_function_symbol (node)
            elif node.kind == clang.cindex.CursorKind.VAR_DECL:
                sym = self.__create_exported_variable_symbol (node)
            elif node.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
                sym = self.__create_macro_symbol (node)
            elif node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                sym = self.__create_typedef_symbol (node)

            if sym is not None:
                self.new_symbols[node.spelling] = sym

    def __create_typedef_symbol (self, node): 
        from hotdoc.core.symbols import (CallbackSymbol, StructSymbol,
                EnumSymbol, AliasSymbol)
        t = node.underlying_typedef_type
        if ast_node_is_function_pointer (t):
            sym = CallbackSymbol (node, self.comments.get (node.spelling))
        else:
            d = t.get_declaration()
            if d.kind == clang.cindex.CursorKind.STRUCT_DECL:
                sym = StructSymbol (node, self.comments.get (node.spelling))
            elif d.kind == clang.cindex.CursorKind.ENUM_DECL:
                sym = EnumSymbol (node, self.comments.get (node.spelling))
            else:
                sym = AliasSymbol (node, self.comments.get (node.spelling))
        return sym

    def __create_macro_symbol (self, node):
        from hotdoc.core.symbols import FunctionMacroSymbol, ConstantSymbol

        l = linecache.getline (str(node.location.file), node.location.line)
        split = l.split()
        if '(' in split[1]:
            sym = FunctionMacroSymbol (node, self.comments.get (node.spelling))
        else:
            sym = ConstantSymbol (node, self.comments.get (node.spelling))

        return sym

    def __create_function_symbol (self, node):
        from hotdoc.core.symbols import FunctionSymbol
        sym = FunctionSymbol (node, self.comments.get (node.spelling))
        return sym

    def __create_exported_variable_symbol (self, node):
        from hotdoc.core.symbols import ExportedVariableSymbol
        sym = ExportedVariableSymbol (node, self.comments.get (node.spelling))
        return sym

    def find_external_symbols(self, nodes, tu):
        for node in nodes:
            node._tu = tu
            if node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
                self.external_symbols[node.spelling] = node
                self.debug ("Found external symbol %s" % node.spelling)

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

    def finalize (self):
        """
        FIXME: We need to cleanup before __del__ because
        clang binding destructors rely on module level
        global variables, which destruction order is undefined
        at termination time ...
        """
        del self.token_groups
        del self.symbols
        del self.external_symbols
        del self.tus

if __name__=="__main__": 
    css = ClangScanner ([sys.argv[1]], '')
    print css.comments
