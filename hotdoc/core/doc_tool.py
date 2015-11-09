import os, sys, argparse

reload(sys)  
sys.setdefaultencoding('utf8')

import cPickle as pickle

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, mapper

from .naive_index import NaiveIndexFormatter
from .links import LinkResolver
from .symbols import *
from .base_extension import BaseExtension
from .alchemy_integration import Base
from .inc_parser import DocTree

from ..utils.utils import all_subclasses
from ..utils.simple_signals import Signal
from ..utils.loggable import Loggable
from ..utils.loggable import init as loggable_init
from ..formatters.html.html_formatter import HtmlFormatter

class ConfigError(Exception):
    pass

class ChangeTracker(object):
    def __init__(self):
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

# FIXME: put all persisted things in an internal folder,
# separate from the output
class DocTool(Loggable):
    def __init__(self):
        Loggable.__init__(self)

        self.output = None
        self.index_file = None
        self.raw_comment_parser = None
        self.doc_parser = None
        self.extensions = []
        self.__comments = {}
        self.__symbols = {}
        self.link_resolver = LinkResolver(self)
        self.incremental = False
        self.comment_updated_signal = Signal()
        self.symbol_updated_signal = Signal()

    def get_symbol(self, name, prefer_class=False):
        sym = self.__symbols.get(name)
        if not sym:
            sym = self.session.query(Symbol).filter(Symbol.unique_name ==
                    name).first()

        if sym:
            # Faster look up next time around
            self.__symbols[name] = sym
            sym.resolve_links(self.link_resolver)
        return sym

    def __update_symbol_comment(self, comment):
        self.session.query(Symbol).filter(Symbol.unique_name ==
                comment.name).update({'comment': comment})
        self.comment_updated_signal(comment)

    def format_symbol(self, symbol_name):
        # FIXME this will be API, raise meaningful errors
        pages = self.doc_tree.symbol_maps.get(symbol_name)
        if not pages:
            return None

        page = pages.values()[0]

        if page.extension_name is None:
            self.formatter = HtmlFormatter(self, [])
        else:
            self.formatter = self.get_formatter(page.extension_name)

        sym = self.get_symbol(symbol_name)
        if not sym:
            return None

        self.formatter.format_symbol(sym) 

        return sym.detailed_description

    def get_or_create_symbol(self, type_, **kwargs):
        unique_name = kwargs.get('unique_name')
        if not unique_name:
            unique_name = kwargs.get('display_name')
            kwargs['unique_name'] = unique_name

        if not unique_name:
            print "WTF babe"

        filename = kwargs.get('filename')
        if filename:
            kwargs['filename'] = os.path.abspath(filename)

        symbol = self.session.query(type_).filter(type_.unique_name == unique_name).first()

        if not symbol:
            symbol = type_()

        for key, value in kwargs.items():
            setattr(symbol, key, value)

        symbol.resolve_links(self.link_resolver)

        if self.incremental:
            self.symbol_updated_signal(symbol)

        self.__symbols[unique_name] = symbol

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

    def __create_change_tracker(self):
        try:
            self.change_tracker = pickle.load(open(os.path.join(self.output,
                'change_tracker.p'), 'rb'))
            self.incremental = True
        except IOError:
            self.change_tracker = ChangeTracker()

    def get_formatter(self, extension_name):
        # FIXME: use a dict ..
        for ext in self.extensions:
            if ext.EXTENSION_NAME == extension_name:
                return ext.get_formatter(self.output_format)
        return None

    def setup(self, args):
        from datetime import datetime

        n = datetime.now()
        self.__setup(args)
        print "core setup takes", datetime.now() - n

        for extension in self.extensions:
            n = datetime.now()
            self.change_tracker.mark_extension_stale_sources(extension)
            extension.setup ()
            self.change_tracker.update_extension_sources_mtimes(extension)
            self.session.flush()
            print "extension", extension.EXTENSION_NAME, 'takes', datetime.now() - n

        n = datetime.now()
        self.doc_tree.resolve_symbols(self)
        print "symbol resolution takes", datetime.now() - n

        n = datetime.now()
        self.session.flush()
        print "flushing takes", datetime.now() - n

    def format (self):
        from datetime import datetime

        n = datetime.now()
        self.formatter = HtmlFormatter(self, [])
        self.formatter.format(self.doc_tree.root)
        print "formatting takes", datetime.now() - n

    def add_comment(self, comment):
        self.__comments[comment.name] = comment
        if self.incremental:
            self.__update_symbol_comment (comment)

    def get_comment (self, name):
        comment = self.__comments.get(name)
        if not comment:
            esym = self.get_symbol(name)
            if esym:
                comment = esym.comment
        return comment

    def __setup (self, args):
        if os.name == 'nt':
            self.datadir = os.path.join(os.path.dirname(__file__), '..', 'share')
        else:
            self.datadir = "/usr/share"

        self.parser = argparse.ArgumentParser()
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

        self.parse_args(args)

    def __setup_output(self):
        if os.path.exists (self.output):
            if not os.path.isdir (self.output):
                self.error ("Specified output exists but is not a directory")
                raise ConfigError ()
        else:
            os.mkdir (self.output)

    def __create_extensions (self, args):
        if args[0].extension_name:
            ext = self.__extension_dict[args[0].extension_name](self, args[0])
            self.extensions.append (ext)

            # FIXME: this is crap
            if self.raw_comment_parser is None:
                self.raw_comment_parser = ext.get_raw_comment_parser()
            if self.doc_parser is None:
                self.doc_parser = ext.get_doc_parser()
            if args[1]:
                args = self.parser.parse_known_args (args[1])
                self.__create_extensions (args)

    def parse_args (self, args):
        args = self.parser.parse_known_args(args)

        self.output = args[0].output
        self.output_format = args[0].output_format
        self.include_paths = args[0].include_paths

        if self.output_format not in ["html"]:
            raise ConfigError ("Unsupported output format : %s" %
                    self.output_format)

        self.__setup_output ()

        # FIXME: we might actually want not to be naive
        if not args[0].index:
            nif = NaiveIndexFormatter (self.c_source_scanner.symbols)
            args[0].index = "tmp_markdown_files/tmp_index.markdown"

        self.index_file = args[0].index

        prefix = os.path.dirname(self.index_file)
        self.doc_tree = DocTree(self, prefix)

        self.__create_extensions (args)

        self.doc_tree.build_tree(self.index_file)
        self.doc_tree.fill_symbol_maps()

        self.__create_change_tracker()

    def persist(self):
        self.session.commit()
        pickle.dump(self.change_tracker, open(os.path.join(self.output,
            'change_tracker.p'), 'wb'))
        self.doc_tree.persist()

    def finalize (self):
        self.session.close()
