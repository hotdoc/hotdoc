import os, sys, argparse

reload(sys)  
sys.setdefaultencoding('utf8')

import pygraphviz as pg
import cPickle as pickle

from hotdoc.core.alchemy_integration import session, finalize_db, purge_db

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


class ChangeTracker(object):
    def __init__(self):
        self.markdown_mtimes = {}
        self.exts_mtimes = {}

    def update_extension_sources_mtimes(self, extension):
        ext_mtimes = {}
        source_files = extension.get_source_files()
        for source_file in source_files:
            mtime = os.path.getmtime(source_file)
            ext_mtimes[source_file] = mtime

        self.exts_mtimes[extension.EXTENSION_NAME] = ext_mtimes

    def mark_extension_stale_sources (self, extension):
        stale = []
        source_files = extension.get_source_files()

        if extension.EXTENSION_NAME in self.exts_mtimes:
            prev_mtimes = self.exts_mtimes[extension.EXTENSION_NAME]
        else:
            prev_mtimes = {}

        for source_file in source_files:
            if not source_file in prev_mtimes:
                stale.append(source_file)
            else:
                prev_mtime = prev_mtimes.get(source_file)
                mtime = os.path.getmtime(source_file)
                if prev_mtime != mtime:
                    stale.append(source_file)

        extension.set_stale_source_files(stale)

class SymbolsTable(object):
    def __init__(self):
        self.symbols_map = {}
        self.pages_symbols = {}

    def listen(self, page_parser):
        page_parser.adding_symbol_signal.connect(self.__adding_symbol_cb)

    def __adding_symbol_cb (self, page, symbol_name):
        symbol_map = self.symbols_map.pop(symbol_name, {})
        symbol_map[page.source_file] = True
        self.symbols_map[symbol_name] = symbol_map

        page_symbols = self.pages_symbols.pop(page.source_file, [])
        page_symbols.append(symbol_name)
        self.pages_symbols[page.source_file] = page_symbols

class DocTool(Loggable):
    def __init__(self):
        Loggable.__init__(self)

        self.output = None
        self.style = None
        self.index_file = None
        self.raw_comment_parser = None
        self.doc_parser = None
        self.page_parser = None
        self.extensions = []
        self.comments = {}
        self.full_scan = False
        self.full_scan_patterns = ['*.h']
        self.link_resolver = LinkResolver()
        self.well_known_names = {}
        self.rebuilding = False

    def __create_symbols_table(self):
        try:
            self.symbols_table = pickle.load(open(os.path.join(self.output,
                'symbols_table.p'), 'rb'))
        except IOError:
            self.symbols_table = SymbolsTable()

        self.symbols_table.listen(self.page_parser)

    def __create_change_tracker(self):
        try:
            self.change_tracker = pickle.load(open(os.path.join(self.output,
                'change_tracker.p'), 'rb'))
        except IOError:
            self.change_tracker = ChangeTracker()

    def parse_and_format (self):
        self.__setup()
        self.parse_args ()

        self.__create_symbols_table()
        self.__create_change_tracker()

        # We're done setting up, extensions can setup too
        for extension in self.extensions:
            print "Doing extension", extension.EXTENSION_NAME
            n = datetime.now()
            self.change_tracker.mark_extension_stale_sources(extension)
            extension.setup ()
            self.change_tracker.update_extension_sources_mtimes(extension)
            purge_db()
            self.comments.update (extension.get_comments())
            print "Extension done", datetime.now() - n, extension.EXTENSION_NAME

        n = datetime.now()
        page = self.page_parser.parse (self.index_file)

        purge_db()

        from ..formatters.html.html_formatter import HtmlFormatter
        self.formatter = HtmlFormatter([])

        self.formatter.format(page)

        print "currently optimizable:", datetime.now() - n

        pickle.dump(self.symbols_table, open(os.path.join(self.output,
            'symbols_table.p'), 'wb'))
        pickle.dump(self.change_tracker, open(os.path.join(self.output,
            'change_tracker.p'), 'wb'))
        session.commit()
        self.finalize()

    def register_well_known_name (self, name, extension):
        self.well_known_names[name] = extension

    def get_well_known_name_handler (self, name):
        return self.well_known_names.get(name)

    def get_symbol (self, name):
        from hotdoc.core.symbols import get_symbol
        return get_symbol(name)

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
        session.close()

doc_tool = DocTool()
