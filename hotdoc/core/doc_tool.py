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

class DependencyEdge(object):
    def __init__(self, parent, child):
        self.parent = parent
        self.child = child

    def __eq__(self, other):
        return (self.parent == other.parent and
                self.child == other.child)

    def __hash__(self):
        return hash((self.parent, self.child))

    def __repr__(self):
        return '%s -> %s' % (self.parent, self.child)

class DependencyNode (object):
    def __init__(self, filename):
        self.filename = filename
        self.unstale()

    def __repr__(self):
        return '%s last modified at %s' % (self.filename, str(self.mtime))

    def unstale(self):
        try:
            self.mtime = os.path.getmtime(self.filename)
        except OSError:
            self.mtime = -1

class DependencyGraph(object):
    def __init__(self):
        self.nodes = {}
        self.edges = set({})

    def add_node (self, filename):
        node = DependencyNode(filename)
        self.nodes[filename] = node

    def add_edge (self, parent, child):
        edge = DependencyEdge(parent, child)
        self.edges.add (edge)

    def dump(self):
        graph = pg.AGraph(directed=True, strict=True)

        for node in self.nodes.values():
            graph.add_node (node.filename, style='rounded', shape='box')
            node.unstale()
        for edge in self.edges:
            graph.add_edge (edge.parent, edge.child)
 
        with open ('dependency.svg', 'w') as f:
            graph.draw(f, prog='dot', format='svg', args="-Grankdir=LR")


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

    def get_stale_files (self, filenames):
        stale = []
        for filename in filenames:
            abspath = os.path.abspath (filename)
            node = self.graph.nodes.get(abspath)
            if not node:
                self.graph.add_node (abspath)
                stale.append (abspath)
                continue
            mtime = os.path.getmtime (abspath)
            if mtime > node.mtime:
                stale.append (abspath)

        return stale

    def dump_dependencies (self, page):
        self.graph.add_node (page.source_file)
        for symbol in page.symbols:
            if symbol.filename:
                self.graph.add_node (symbol.filename)
                self.graph.add_edge (page.source_file, symbol.filename)
            if symbol.comment and symbol.comment.filename:
                self.graph.add_node (symbol.comment.filename)
                self.graph.add_edge(page.source_file, symbol.comment.filename)

        for cpage in page.subpages:
            self.graph.add_node (cpage.source_file)
            self.graph.add_edge (page.source_file, cpage.source_file)
            self.dump_dependencies (cpage)

    def parse_and_format (self):
        self.__setup()
        self.parse_args ()

        try:
            self.graph = pickle.load(open(os.path.join(self.output,
                'dep_graph.p'), 'rb'))
            self.rebuilding = True
        except IOError:
            self.graph = DependencyGraph()

        # We're done setting up, extensions can setup too
        for extension in self.extensions:
            print "Doing extension", extension.EXTENSION_NAME
            n = datetime.now()
            extension.setup ()
            purge_db()
            self.comments.update (extension.get_comments())
            print "Extension done", datetime.now() - n, extension.EXTENSION_NAME

        n = datetime.now()
        page = self.page_parser.parse (self.index_file)

        purge_db()

        self.dump_dependencies (page)
        from ..formatters.html.html_formatter import HtmlFormatter
        self.formatter = HtmlFormatter([])

        self.formatter.format(page)

        print "currently optimizable:", datetime.now() - n

        self.graph.dump()
        pickle.dump(self.graph, open(os.path.join(self.output, 'dep_graph.p'), 'wb'))
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
