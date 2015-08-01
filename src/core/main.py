import argparse, os

import sys
import types
from utils import loggable

# FIXME remove these deps
from giscanner.annotationparser import GtkDocCommentBlockParser
from giscanner.message import MessageLogger

from datetime import datetime

# FIXME: allow specification of the formatter on the command line
from formatters.html_formatter import HtmlFormatter

from clang_interface.clangizer import ClangScanner

# FIXME extensions should be customizable too ..
from extensions.GIExtension import GIExtension

from naive_index import NaiveIndexFormatter
from utils.utils import PkgConfig

def main (args):
    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--style", action="store", default="gnome",
            dest="style")
    parser.add_argument ("-f", "--filenames", action="store", nargs="+",
            dest="filenames")
    parser.add_argument ("-i", "--index", action="store",
            dest="index")
    parser.add_argument ("-o", "--output", action="store",
            dest="output", required=True)
    parser.add_argument ("--gobject-introspection-dump", action="store",
            dest="gobject_introspection_dump")

    logger = MessageLogger.get(namespace=None)

    loggable.init("DOC_DEBUG")
    args = parser.parse_args(args[1:])

    if os.path.exists (args.output):
        if not os.path.isdir (args.output):
            loggable.error ("Specified output exists but is not a directory", "")
            return
    else:
        os.mkdir (args.output)

    if args.style == "gnome":
        css = ClangScanner (args.filenames)
        n = datetime.now()
        cbp = GtkDocCommentBlockParser()
        blocks = cbp.parse_comment_blocks(css.comments)
        loggable.info("Comment block parsing done in %s" % str(datetime.now() -n), "")
    elif args.style == "doxygen":
        css = ClangScanner (args.filenames, full_scan=True,
                full_scan_patterns=['*.c', '*.h'])
        blocks = None
    else:
        loggable.error ("style not handled : %s" % args.style, "")
        sys.exit (0)

    extensions = []
    if args.gobject_introspection_dump:
        extensions.append (GIExtension(args.gobject_introspection_dump))

    if not args.index:
        nif = NaiveIndexFormatter (css.symbols)
        args.index = tmp_markdown_files/tmp_index.markdown

    formatter = HtmlFormatter (css, blocks, [], args.index, args.output,
            extensions)
    formatter.format()
