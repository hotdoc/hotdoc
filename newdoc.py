import argparse, os

import dagger

from giscanner.annotationparser import GtkDocCommentBlockParser
import sys
import shlex
import subprocess
import types
import loggable

from giscanner.message import MessageLogger
from datetime import datetime
from gnome_markdown_filter import GnomeMarkdownFilter
from pandocfilters import BulletList
from pandoc_interface.pandoc_client import pandoc_converter
from html_formatter import HtmlFormatter
from xml.etree.cElementTree import parse, tostring
from clangizer import ClangScanner
from gi_extension import GIExtension
from naive_index import NaiveIndexFormatter

def PkgConfig(args):
    cmd = ['pkg-config'] + shlex.split(args)
    out = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE).stdout
    line = out.readline()[:-1].split(" ")
    return filter(lambda a: a != ' ', line)


def main (args):
    parser = argparse.ArgumentParser()

    parser.add_argument("--packages", nargs="+",
                      action="store", dest="packages",
                      help="CFlags for source scanning")
    parser.add_argument("-I", nargs="+",
                      action="store", dest="cpp_includes", default=[],
                      help="Pre processor include files")
    parser.add_argument("-D", nargs="+",
                      action="store", dest="cpp_defines",
                      help="Pre processor defines")
    parser.add_argument("-U", nargs="+",
                      action="store", dest="cpp_undefines",
                      help="Pre processor undefines")
    parser.add_argument("-s", "--style", action="store", default="gnome",
            dest="style")
    parser.add_argument ("-f", "--filenames", action="store", nargs="+",
            dest="filenames")
    parser.add_argument ("-i", "--index", action="store",
            dest="index")
    parser.add_argument ("--gobject-introspection-dump", action="store",
            dest="gobject_introspection_dump")

    logger = MessageLogger.get(namespace=None)

    loggable.init("DOC_DEBUG")
    args = parser.parse_args(args[1:])


    cflags = []
    if args.packages:
        for p in args.packages:
            includes = PkgConfig ("--cflags %s" % p)
            for include in includes:
                if include:
                    cflags.append (include)

    cpp_includes = []
    for i in args.cpp_includes:
        cpp_includes.append (os.path.realpath (i))
    args.cpp_includes = cpp_includes

    print args.style
    if args.style == "gnome":
        css = ClangScanner (args.filenames)
        n = datetime.now()
        cbp = GtkDocCommentBlockParser()
        blocks = cbp.parse_comment_blocks(css.comments)
        Loggable.info("Comment block parsing done" % str(datetime.now() - n))
    elif args.style == "doxygen":
        css = ClangScanner (args.filenames, full_scan=True,
                full_scan_patterns=['*.c', '*.h'])
        dbp = DoxygenCommentBlockParser()
        dbp.parse_comment_blocks (css.symbols)
        return
    else:
        loggable.error ("style not handled : %s" % args.style)
        sys.exit (0)


    extensions = []
    if args.gobject_introspection_dump:
        extensions.append (GIExtension.GIExtension(args.gobject_introspection_dump))

    if not args.index:
        nif = NaiveIndexFormatter (css.symbols)
        sys.exit(0)

    formatter = HtmlFormatter (css, blocks, [], args.index, "gst",
            extensions)
    formatter.format()
