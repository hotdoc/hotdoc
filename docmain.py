import argparse, os

from lxml import etree as ET
from giscanner.transformer import Transformer
import logging
import sys

from base_formatter import Formatter, add_missing_symbols
from sections import SectionsGenerator
from datetime import datetime
from markdown_sections import SectionFilter

class StupidFormatter (Formatter):
    pass

def doc_main (args):
    try:
        debug_level = os.environ["DOCTOOL_DEBUG"]
        if debug_level.lower() == "info":
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.DEBUG)
    except KeyError:
        pass

    parser = argparse.ArgumentParser()

    parser.add_argument("girfile")
    parser.add_argument("-o", "--output",
                      action="store", dest="output",
                      help="Directory to write output to")
    parser.add_argument("-l", "--language",
                      action="store", dest="language",
                      default="c",
                      help="Output language")
    parser.add_argument("-I", "--add-include-path",
                      action="append", dest="include_paths", default=[],
                      help="include paths for other GIR files")
    parser.add_argument("-M", "--markdown-include-path",
                      action="append", dest="markdown_include_paths", default=[],
                      help="include paths for markdown inclusion")
    parser.add_argument("-s", "--write-sections-file",
                      action="store_true", dest="write_sections",
                      help="Generate and write out a sections file")
    parser.add_argument("-u", "--sections-file",
                      action="store", dest="sections_file",
                      help="Sections file to use for ordering")
    parser.add_argument("-i", "-index",
                      action="store", dest="index",
                      help="Sections index")
    parser.add_argument("-O", "--online-links",
                      action="store_true", dest="online_links",
                      help="Generate online links")
    parser.add_argument("-g", "--link-to-gtk-doc",
                      action="store_true", dest="link_to_gtk_doc",
                      help="Link to gtk-doc documentation, the documentation "
                      "packages to link against need to be installed in "
                      "/usr/share/gtk-doc")
    parser.add_argument("-m", "--add-missing-symbols", action="store_true",
            dest="add_missing_symbols", help="Add missing symbols to an "
            "existing sections file, which must comply to the new scheme")

    args = parser.parse_args(args[1:])
    if not args.output:
        raise SystemExit("missing output parameter")

    print os.path.dirname (args.index)

    if 'UNINSTALLED_INTROSPECTION_SRCDIR' in os.environ:
        top_srcdir = os.environ['UNINSTALLED_INTROSPECTION_SRCDIR']
        top_builddir = os.environ['UNINSTALLED_INTROSPECTION_BUILDDIR']
        extra_include_dirs = [os.path.join(top_srcdir, 'gir'), top_builddir]
    else:
        extra_include_dirs = []
    extra_include_dirs.extend(args.include_paths)
    transformer = Transformer.parse_from_gir(args.girfile, extra_include_dirs)

    """
    if not args.sections_file:
        sections_generator = SectionsGenerator (transformer)
        sections = sections_generator.generate (args.output)
    else:
        sections = ET.parse (args.sections_file)
    """

    if args.add_missing_symbols:
        add_missing_symbols (transformer, sections)
        sys.exit (0)

    from slate_markdown_formatter import SlateMarkdownFormatter
    from html_formatter import HtmlFormatter

    formatter = HtmlFormatter (transformer, args.markdown_include_paths,
            None, args.index, args.output, do_class_aggregation=True)
    print ("Actually starting work")
    n = datetime.now()
    formatter.format (args.output)
    print "done", datetime.now() - n
