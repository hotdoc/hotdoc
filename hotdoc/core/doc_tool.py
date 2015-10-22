import os, sys, argparse

reload(sys)  
sys.setdefaultencoding('utf8')

from .naive_index import NaiveIndexFormatter
from .links import LinkResolver
from .base_extension import BaseExtension

from ..utils.utils import all_subclasses
from ..utils.simple_signals import Signal
from ..utils.loggable import Loggable
from ..utils.loggable import init as loggable_init

from datetime import datetime

def merge_dicts(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result

class ConfigError(Exception):
    pass

class DocTool(Loggable):
    def __init__(self):
        Loggable.__init__(self)

        self.output = None
        self.c_sources = None
        self.style = None
        self.index_file = None
        self.raw_comment_parser = None
        self.doc_parser = None
        self.symbol_factory = None
        self.page_parser = None
        self.extensions = []
        self.pages = []
        self.comments = {}
        self.symbols = {}
        self.full_scan = False
        self.full_scan_patterns = ['*.h']
        self.link_resolver = LinkResolver()
        self.well_known_names = {}
        self.queued_well_known_names = []

    def parse_and_format (self):
        self.__setup()
        self.parse_args ()

        # We're done setting up, extensions can setup too
        for extension in self.extensions:
            extension.setup ()
            self.symbols.update (extension.get_extra_symbols())
            self.comments.update (extension.get_comments())

        page = self.page_parser.parse (self.index_file)

        from ..formatters.html.html_formatter import HtmlFormatter
        self.formatter = HtmlFormatter([])
        self.base_formatter = self.formatter

        self.formatter.format(page)

        while self.queued_well_known_names:
            wkn = self.queued_well_known_names.pop()
            extension = self.well_known_names[wkn]
            formatter = extension.get_formatter(self.output_format)
            if formatter:
                self.formatter = formatter
            page = extension.create_page_from_well_known_name (wkn)
            self.formatter.format (page)

        self.finalize()

    def register_well_known_name (self, name, extension):
        self.well_known_names[name] = extension

    def get_well_known_name_handler (self, name):
        return self.well_known_names.get(name)

    def queue_well_known_name (self, name):
        self.queued_well_known_names.insert (0, name)

    def get_symbol (self, name):
        return self.symbols.get (name)

    def __setup (self):
        if os.name == 'nt':
            self.datadir = os.path.join(os.path.dirname(__file__), '..', 'share')
        else:
            self.datadir = "/usr/share"

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-s", "--style", action="store", default="gnome",
                dest="style")
        self.parser.add_argument ("-i", "--index", action="store",
                dest="index", help="location of the index file")
        self.parser.add_argument ("-o", "--output", action="store", default='doc',
                dest="output", help="where to output the rendered documentation")
        self.parser.add_argument ("--output-format", action="store",
                default="html", dest="output_format")
        self.parser.add_argument ("-I", "--include-path", action="append",
                default=[], dest="include_paths")

        # Hardcoded for now
        from ..extensions.common_mark_parser import CommonMarkParser
        self.page_parser = CommonMarkParser ()

        extension_subclasses = all_subclasses (BaseExtension)
        subparsers = self.parser.add_subparsers (title="extensions",
                                            help="Extensions for parsing and formatting documentation",
                                            dest="extension_name")
        self.__extension_dict = {}
        for subclass in extension_subclasses:
            subparser = subparsers.add_parser(subclass.EXTENSION_NAME)
            subclass.add_arguments (subparser)
            self.__extension_dict[subclass.EXTENSION_NAME] = subclass

        loggable_init("DOC_DEBUG")

    def __setup_output(self):
        if os.path.exists (self.output):
            if not os.path.isdir (self.output):
                self.error ("Specified output exists but is not a directory")
                raise ConfigError ()
        else:
            os.mkdir (self.output)

    def __setup_source_scanners(self, clang_options):
        from ..clang_interface.clangizer import ClangScanner
        self.c_source_scanner = ClangScanner (self, clang_options)
        self.symbols = self.c_source_scanner.new_symbols

        if self.c_sources and not self.symbols:
            raise ConfigError ("No symbols found in c sources")

    def __parse_extensions (self, args):
        if args[0].extension_name:
            ext = self.__extension_dict[args[0].extension_name](args[0])
            self.extensions.append (ext)

            if self.raw_comment_parser is None:
                self.raw_comment_parser = ext.get_raw_comment_parser()
            if self.doc_parser is None:
                self.doc_parser = ext.get_doc_parser()
            if args[1]:
                args = self.parser.parse_known_args (args[1])
                self.__parse_extensions (args)

    def parse_args (self):
        args = self.parser.parse_known_args()

        self.output = args[0].output
        self.output_format = args[0].output_format
        self.style = args[0].style
        self.include_paths = args[0].include_paths

        if self.output_format not in ["html"]:
            raise ConfigError ("Unsupported output format : %s" %
                    self.output_format)

        self.__setup_output ()
        self.__parse_extensions (args)

        if not args[0].index:
            nif = NaiveIndexFormatter (self.c_source_scanner.symbols)
            args[0].index = "tmp_markdown_files/tmp_index.markdown"
        self.index_file = args[0].index

    def finalize (self):
        self.link_resolver.pickle (self.output)


doc_tool = DocTool()
