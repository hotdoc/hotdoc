import os, sys, argparse

reload(sys)  
sys.setdefaultencoding('utf8')

import pygraphviz as pg
import cPickle as pickle

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, mapper

from .naive_index import NaiveIndexFormatter
from .links import LinkResolver
from .symbols import Symbol
from .base_extension import BaseExtension
from .alchemy_integration import Base
from .inc_parser import DocTree

from ..utils.utils import all_subclasses
from ..utils.simple_signals import Signal
from ..utils.loggable import Loggable
from ..utils.loggable import init as loggable_init
from ..formatters.html.html_formatter import HtmlFormatter
from ..extensions.common_mark_parser import CommonMarkParser

from datetime import datetime

class ConfigError(Exception):
    pass

class ChangeTracker(object):
    def __init__(self):
        self.pages_mtimes = {}
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

    def __update_page_mtime(self, page):
        try:
            self.pages_mtimes[page.source_file] = os.path.getmtime(page.source_file)
        except OSError:  # Generated pages
            pass

        for cpage in page.subpages:
            self.__update_page_mtime (cpage)

    def update_pages_mtimes(self, page):
        self.__update_page_mtime (page)

        # Check removed markdown files
        for source_file in self.pages_mtimes:
            if not os.path.exists (source_file):
                self.pages_mtimes.pop(source_file)

    def get_stale_pages(self):
        stale = set({})

        for source_file, prev_mtime in self.pages_mtimes.items():
            try:
                mtime = os.path.getmtime(source_file)
            except OSError:  # Page might have been deleted
                continue
            if mtime != prev_mtime:
                stale.add(source_file)

        return stale

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
        self.extensions = []
        self.__comments = {}
        self.full_scan = False
        self.full_scan_patterns = ['*.h']
        self.link_resolver = LinkResolver(self)
        self.well_known_names = {}
        self.stale_pages = set({})
        self.final_stale_pages = None
        self.incremental = False
        self.symbols_maps = {}

    def get_symbol(self, name):
        sym = self.session.query(Symbol).filter(Symbol.name == name).first()
        if sym:
            sym.resolve_links(self.link_resolver)
        return sym

    def mark_stale_pages(self, symbol_name):
        containing_pages = self.symbols_maps.get(symbol_name)
        if containing_pages is not None:
            for source_file, page in containing_pages.items():
                if not page.is_stale:
                    page.is_stale = True
                    self.doc_tree.page_parser.reparse(page)
                self.stale_pages.add(page)

    def get_or_create_symbol(self, type_, **kwargs):
        name = kwargs.pop('name')

        filename = kwargs.get('filename')
        if filename:
            kwargs['filename'] = os.path.abspath(filename)

        symbol = self.session.query(type_).filter(type_.name == name).first()

        if not symbol:
            symbol = type_(name=name)

        for key, value in kwargs.items():
            setattr(symbol, key, value)

        symbol.resolve_links(self.link_resolver)

        if self.incremental:
            self.mark_stale_pages(symbol.name)

        return symbol

    def __setup_database(self):
        self.engine = create_engine('sqlite:///hotdoc.db')
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.session.autoflush = False
        Base.metadata.create_all(self.engine)
        event.listen(mapper, 'init', self.__auto_add)

    def __auto_add (self, target, args, kwargs):
        self.session.add (target)

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

    def get_formatter(self, extension_name):
        for ext in self.extensions:
            if ext.EXTENSION_NAME == extension_name:
                return ext.get_formatter(self.output_format)
        return None

    def __resolve_page_symbols(self, page):
        page.resolve_symbols(self)
        for pagename in page.subpages:
            cpage = self.pages[pagename]
            self.__resolve_page_symbols(cpage)

    def page_is_stale(self, page):
        if self.final_stale_pages is None:
            return True

        if page.source_file in self.final_stale_pages:
            return True

        return False

    def __get_parsed_pages(self, page, all_pages):
        if not self.page_is_stale (page):
            all_pages[page.source_file] = page
        for cpage in page.subpages:
            self.__get_parsed_pages(cpage, all_pages)

    def __display_page_tree(self, page, level=0):
        print '  ' * level, page.source_file
        for cpage in page.subpages:
            self.__display_page_tree(cpage, level + 1)

    def __fill_symbols_map(self):
        for page in self.doc_tree.pages.values():
            for name in page.symbol_names:
                symbol_map = self.symbols_maps.pop(name, {})
                symbol_map[page.source_file] = page
                self.symbols_maps[name] = symbol_map

    def parse_and_format (self):
        self.__setup()
        self.parse_args ()

        self.root = self.doc_tree.build_tree(self.index_file)
        self.__fill_symbols_map()

        #self.__create_symbols_table()
        self.__create_change_tracker()


        # We're done setting up, extensions can setup too
        for extension in self.extensions:
            print "Doing extension", extension.EXTENSION_NAME
            n = datetime.now()
            self.change_tracker.mark_extension_stale_sources(extension)
            extension.setup ()
            self.change_tracker.update_extension_sources_mtimes(extension)
            self.session.flush()
            self.__comments.update (extension.get_comments())
            print "Extension done", datetime.now() - n, extension.EXTENSION_NAME

        self.session.flush()

        if self.incremental:
            for comment in self.__comments.values():
                self.mark_stale_pages(comment.name)
            self.final_stale_pages = set({})
            for page in self.doc_tree.pages.values():
                if page.is_stale:
                    self.final_stale_pages.add (page.source_file)
            self.final_stale_pages |= self.stale_pages

        print "ze stale pages are", self.final_stale_pages

        self.formatter = HtmlFormatter(self, [])
        self.formatter.format(self.root)

        print "currently optimizable:", datetime.now() - n

        #pickle.dump(self.symbols_table, open(os.path.join(self.output,
        #    'symbols_table.p'), 'wb'))
        pickle.dump(self.change_tracker, open(os.path.join(self.output,
            'change_tracker.p'), 'wb'))
        pickle.dump(self.pages, open('pages.p', 'wb'))
        #pickle.dump(page, open(os.path.join(self.output, 'index.p'), 'wb'))
        self.session.commit()
        self.finalize()

    def register_well_known_name (self, name, extension):
        self.well_known_names[name] = extension

    def get_well_known_name_handler (self, name):
        return self.well_known_names.get(name)

    def get_comment (self, name):
        return self.__comments.get(name)

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

        self.__setup_database()

    def __setup_output(self):
        if os.path.exists (self.output):
            if not os.path.isdir (self.output):
                self.error ("Specified output exists but is not a directory")
                raise ConfigError ()
        else:
            os.mkdir (self.output)

    def __parse_extensions (self, args):
        if args[0].extension_name:
            ext = self.__extension_dict[args[0].extension_name](self, args[0])
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

        if not args[0].index:
            nif = NaiveIndexFormatter (self.c_source_scanner.symbols)
            args[0].index = "tmp_markdown_files/tmp_index.markdown"
        self.index_file = args[0].index

        try:
            self.pages = pickle.load(open('pages.p', 'rb'))
            self.incremental = True
        except:
            self.pages = {}

        prefix = os.path.dirname(self.index_file)
        self.doc_tree = DocTree(self.pages, prefix)

        self.__parse_extensions (args)

    def finalize (self):
        self.session.close()
