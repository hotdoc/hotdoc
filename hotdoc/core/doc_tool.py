"""
Core of the core.
"""

import argparse
import cPickle as pickle
import json
import os
import shutil
import sys
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hotdoc.core.alchemy_integration import Base
from hotdoc.core.base_formatter import Formatter
from hotdoc.core.change_tracker import ChangeTracker
from hotdoc.core.comment_block import Comment, Tag
from hotdoc.core.doc_tree import DocTree
from hotdoc.core.gi_raw_parser import GtkDocRawCommentParser
from hotdoc.core.links import LinkResolver, Link
from hotdoc.core.symbols import Symbol
from hotdoc.formatters.html.html_formatter import HtmlFormatter
from hotdoc.utils.loggable import TerminalController
from hotdoc.utils.simple_signals import Signal
from hotdoc.utils.utils import get_all_extension_classes
from hotdoc.utils.wizard import (QUICKSTART_HELP, QuickStartArgument,
                                 QuickStartWizard, Skip)

try:
    from hotdoc.utils.git_interface import GitInterface
    HAVE_GIT_INTERFACE = True
except ImportError:
    HAVE_GIT_INTERFACE = False


class ConfigError(Exception):
    """
    Banana banana
    """
    pass


HOTDOC_ASCII =\
    r"""
/**    __  __   ____     ______   ____     ____     ______
 *    / / / /  / __ \   /_  __/  / __ \   / __ \   / ____/
 *   / /_/ /  / / / /    / /    / / / /  / / / /  / /
 *  / __  /  / /_/ /    / /    / /_/ /  / /_/ /  / /___
 * /_/ /_/   \____/    /_/    /_____/   \____/   \____/
 *
 * The Tastiest Documentation Tool.
 */
"""

PROMPT_GIT_REPO =\
    """
If you use git, I can commit the files created or
modified during setup, you will be prompted for confirmation
when that is the case.

The author name and mail address will be 'hotdoc' and
'hotdoc@hotdoc.net'.

Note: here as everywhere else, you can answer None to
skip the question.
"""

# pylint: disable=unused-argument


def validate_git_repo(wizard, path):
    """
    Banana banana
    """
    try:
        GitInterface(path)
        return True
    # pylint: disable=broad-except
    except Exception:
        print "This does not look like a git repo : %s" % path
        return False

PROMPT_ROOT_INDEX =\
    """
I can now create a root index to tie all your sub indexes
together, do you wish me to do that [y,n]? """


class HotdocWizard(QuickStartWizard):
    """
    Banana banana
    """
    # pylint: disable=no-member

    def __init__(self, *args, **kwargs):
        conf_path = kwargs.pop('conf_path', '')
        QuickStartWizard.__init__(self, *args, **kwargs)
        if self.parent == self:
            self.comments = {}
            self.symbols = {}
            self.term_controller = TerminalController()
            if HAVE_GIT_INTERFACE:
                self.git_interface = GitInterface()
            else:
                self.git_interface = None
            self.config = {}
            self.conf_path = conf_path
        else:
            self.comments = self.parent.comments
            self.symbols = self.parent.symbols
            self.term_controller = self.parent.term_controller
            self.git_interface = self.parent.git_interface
            self.conf_path = self.parent.conf_path

        self.tag_validators = {}

    def add_comment(self, comment):
        """
        Banana banana
        """
        self.comments[comment.name] = comment

    def get_comment(self, name):
        """
        Banana banana
        """
        return self.comments.get(name)

    def get_or_create_symbol(self, type_, **kwargs):
        """
        Banana banana
        """
        unique_name = kwargs.get('unique_name')
        if not unique_name:
            unique_name = kwargs.get('display_name')
            kwargs['unique_name'] = unique_name

        filename = kwargs.get('filename')
        if filename:
            kwargs['filename'] = os.path.abspath(filename)

        symbol = type_()

        for key, value in kwargs.items():
            setattr(symbol, key, value)

        self.symbols[unique_name] = symbol

        return symbol

    def resolve_config_path(self, path):
        """
        Banana banana
        """
        if path is None:
            return path

        res = os.path.join(self.conf_path, path)
        return os.path.abspath(res)

    def before_prompt(self):
        """
        Banana banana
        """
        self.__clear_screen()

    # pylint: disable=no-self-use
    def get_index_path(self):
        """
        Banana banana
        """
        return None

    # pylint: disable=no-self-use
    def get_index_name(self):
        """
        Banana banana
        """
        return None

    def __create_root_index(self):
        contents = 'Welcome to our documentation!\n'

        for obj in self._qs_objects:
            if isinstance(obj, HotdocWizard):
                index_path = obj.get_index_path()
                index_name = obj.get_index_name()
                if index_path:
                    contents += '\n#### [%s](%s)\n' % (index_name, index_path)

        path = self.prompt_key(
            'index_path',
            prompt='Path to save the created index in',
            store=False,
            validate_function=QuickStartWizard.validate_folder)

        path = os.path.join(path, 'index.markdown')

        with open(path, 'w') as _:
            _.write(contents)

        self.config['index'] = path

    def before_quick_start(self, obj):
        """
        Banana banana
        """
        # pylint: disable=unidiomatic-typecheck
        if type(obj) == QuickStartArgument and obj.argument.dest == 'index':
            if self.config.get('index'):
                return

            self.before_prompt()
            if self.ask_confirmation(PROMPT_ROOT_INDEX):
                self.__create_root_index()
                raise Skip

    def main_prompt(self):
        """
        Banana banana
        """
        prompt = self.term_controller.BOLD +\
            "\nHotdoc started without arguments, starting setup\n" +\
            self.term_controller.NORMAL
        prompt += self.term_controller.CYAN + \
            QUICKSTART_HELP + self.term_controller.NORMAL

        prompt += '\nPress Enter to start setup '
        if not self.wait_for_continue(prompt):
            return False

        if not HAVE_GIT_INTERFACE:
            return True

        try:
            repo_path = self.prompt_key(
                'git_repo', prompt=">>> Path to the git repo ? ",
                title="the path to the root of the git repository",
                extra_prompt=PROMPT_GIT_REPO,
                validate_function=validate_git_repo,
                finalize_function=HotdocWizard.finalize_path)
            self.git_interface.set_repo_path(
                self.resolve_config_path(repo_path))
        except Skip:
            pass

        return True

    @staticmethod
    def finalize_path(wizard, path):
        """
        Banana banana
        """
        if not path:
            return path

        return os.path.relpath(path, wizard.conf_path)

    @staticmethod
    def finalize_paths(wizard, paths):
        """
        Banana banana
        """
        if not paths:
            return paths

        res = []

        for path in paths:
            res.append(os.path.relpath(path, wizard.conf_path))

        return res

    def __clear_screen(self):
        sys.stdout.write(self.term_controller.CLEAR_SCREEN)
        sys.stdout.write(self.term_controller.RED +
                         self.term_controller.BOLD + HOTDOC_ASCII +
                         self.term_controller.NORMAL)

    def _add_argument_override(self, group, *args, **kwargs):
        set_default = kwargs.get('default')
        kwargs['default'] = argparse.SUPPRESS
        res = QuickStartWizard._add_argument_override(
            self, group, *args, **kwargs)

        if set_default:
            self.config[res.dest] = set_default

        return res

SUBCOMMAND_DESCRIPTION = """
Valid subcommands.

Exactly one subcommand is required.
Run hotdoc {subcommand} -h for more info
"""


class DocTool(object):
    """
    Banana banana
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self):
        self.session = None
        self.output = None
        self.index_file = None
        self.doc_parser = None
        self.engine = None
        self.wizard = None
        self.doc_tree = None
        self.conf_file = None
        self.formatter = None
        self.git_repo_path = None
        self.change_tracker = None
        self.output_format = None
        self.include_paths = None
        self.html_theme_path = None
        self.editing_server = None
        self.extension_classes = {}
        self.extensions = {}
        self.__comments = {}
        self.__symbols = {}
        self.reference_map = defaultdict(set)
        self.tag_validators = {}
        self.raw_comment_parser = GtkDocRawCommentParser(self)
        self.link_resolver = LinkResolver(self)
        self.incremental = False
        self.comment_updated_signal = Signal()
        self.symbol_updated_signal = Signal()

        if os.name == 'nt':
            self.datadir = os.path.join(
                os.path.dirname(__file__), '..', 'share')
        else:
            self.datadir = "/usr/share"

    def get_symbol(self, name, prefer_class=False):
        """
        Banana banana
        """
        sym = self.__symbols.get(name)

        if not self.incremental:
            if sym:
                sym.resolve_links(self.link_resolver)
            return sym

        if not sym:
            sym = self.session.query(Symbol).filter(Symbol.unique_name ==
                                                    name).first()

        if sym:
            # Faster look up next time around
            self.__symbols[name] = sym
            sym.resolve_links(self.link_resolver)
        return sym

    def __update_symbol_comment(self, comment):
        self.session.query(Symbol).filter(
            Symbol.unique_name ==
            comment.name).update({'comment': comment})
        esym = self.__symbols.get(comment.name)
        if esym:
            esym.comment = comment
        self.comment_updated_signal(comment)

    def register_tag_validator(self, validator):
        """
        Banana banana
        """
        self.tag_validators[validator.name] = validator

    def format_symbol(self, symbol_name):
        """
        Banana banana
        """
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

        self.update_doc_parser(page.extension_name)

        sym.update_children_comments()
        old_server = self.formatter.editing_server
        self.formatter.editing_server = None
        self.formatter.format_symbol(sym)
        self.formatter.editing_server = old_server

        return sym.detailed_description

    def patch_page(self, symbol, raw_comment):
        """
        Banana banana
        """
        pages = self.doc_tree.symbol_maps.get(symbol.unique_name)
        if not pages:
            return False

        old_comment = symbol.comment
        new_comment = self.raw_comment_parser.parse_comment(
            raw_comment,
            old_comment.filename,
            old_comment.lineno,
            old_comment.lineno + raw_comment.count('\n'))

        if new_comment is None:
            return False

        if new_comment.name != symbol.unique_name:
            return False

        pages = pages.values()
        symbol.comment = new_comment
        for page in pages:
            formatter = self.get_formatter(page.extension_name)
            formatter.patch_page(page, symbol)

        return True

    def get_or_create_symbol(self, type_, **kwargs):
        """
        Banana banana
        """
        unique_name = kwargs.get('unique_name')
        if not unique_name:
            unique_name = kwargs.get('display_name')
            kwargs['unique_name'] = unique_name

        filename = kwargs.get('filename')
        if filename:
            kwargs['filename'] = os.path.abspath(filename)

        if self.incremental:
            symbol = self.session.query(type_).filter(
                type_.unique_name == unique_name).first()
        else:
            symbol = None

        if not symbol:
            symbol = type_()
            self.session.add(symbol)

        for key, value in kwargs.items():
            setattr(symbol, key, value)

        if not symbol.comment:
            symbol.comment = Comment(symbol.unique_name)
            self.add_comment(symbol.comment)

        symbol.resolve_links(self.link_resolver)

        if self.incremental:
            self.symbol_updated_signal(symbol)

        self.__symbols[unique_name] = symbol

        return symbol

    def __setup_database(self):
        if self.session is not None:
            return

        db_path = os.path.join(self.get_private_folder(), 'hotdoc.db')
        self.engine = create_engine('sqlite:///%s' % db_path)
        self.session = sessionmaker(bind=self.engine)()
        self.session.autoflush = False
        Base.metadata.create_all(self.engine)

    def __load_reference_map(self):
        try:
            self.reference_map = \
                pickle.load(open(os.path.join(self.get_private_folder(),
                                              'reference_map.p'), 'rb'))
        except IOError:
            pass

    def __create_change_tracker(self):
        try:
            self.change_tracker = \
                pickle.load(open(os.path.join(self.get_private_folder(),
                                              'change_tracker.p'), 'rb'))
            if self.change_tracker.hard_dependencies_are_stale():
                raise IOError
            self.incremental = True
            print "Building incrementally"
        # pylint: disable=broad-except
        except Exception:
            print "Building from scratch"
            shutil.rmtree(self.get_private_folder(), ignore_errors=True)
            shutil.rmtree(self.output, ignore_errors=True)
            self.change_tracker = ChangeTracker()

    def get_formatter(self, extension_name):
        """
        Banana banana
        """
        ext = self.extensions.get(extension_name)
        if ext:
            return ext.get_formatter(self.output_format)
        return None

    def update_doc_parser(self, extension_name):
        """
        Banana banana
        """
        ext = self.extensions.get(extension_name)
        self.doc_parser = None
        if ext:
            self.doc_parser = ext.get_doc_parser()

    def setup(self, args):
        """
        Banana banana
        """
        self.__setup(args)

        for extension in self.extensions.values():
            extension.setup()
            self.session.flush()

        root = self.doc_tree.pages.get(self.index_file)
        self.doc_tree.resolve_symbols(self, root)

        self.session.flush()

    def get_assets_path(self):
        """
        Banana banana
        """
        return os.path.join(self.output, 'assets')

    def __link_referenced_cb(self, link):
        self.reference_map[link.id_].add(
            self.formatter.current_page.source_file)
        self.formatter.current_page.reference_map.add(link.id_)
        return None

    def __formatting_page_cb(self, formatter, page):
        for link_id in page.reference_map:
            self.reference_map.get(link_id, set()).discard(page.source_file)
        page.reference_map = set()
        return None

    def __create_navigation_script(self, root):
        # Wrapping this is in a javascript file to allow
        # circumventing stupid chrome same origin policy
        site_navigation = self.formatter.format_site_navigation(root)
        path = os.path.join(self.output,
                            self.formatter.get_assets_path(),
                            'js',
                            'site_navigation.js')
        site_navigation = site_navigation.replace('\n', '')
        site_navigation = site_navigation.replace('"', '\\"')
        js_wrapper = 'site_navigation_downloaded_cb("'
        js_wrapper += site_navigation
        js_wrapper += '");'
        with open(path, 'w') as _:
            _.write(js_wrapper.encode('utf-8'))

    def format(self):
        """
        Banana banana
        """
        self.__setup_folder(self.output)
        self.formatter = HtmlFormatter(self, [])
        root = self.doc_tree.pages.get(self.index_file)

        Formatter.formatting_page_signal.connect(self.__formatting_page_cb)
        Link.resolving_link_signal.connect(self.__link_referenced_cb)
        self.formatter.format(root)
        self.__create_navigation_script(root)

    def add_comment(self, comment):
        """
        Banana banana
        """
        self.__comments[comment.name] = comment
        for validator in self.tag_validators.values():
            if validator.default and validator.name not in comment.tags:
                comment.tags[validator.name] = \
                    Tag(name=validator.name,
                        description=validator.default)
        if self.incremental:
            self.__update_symbol_comment(comment)

    def get_comment(self, name):
        """
        Banana banana
        """
        comment = self.__comments.get(name)
        if not comment:
            esym = self.get_symbol(name)
            if esym:
                comment = esym.comment
        return comment

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    def __setup(self, args):
        parser = \
            argparse.ArgumentParser(
                formatter_class=argparse.RawDescriptionHelpFormatter,)

        subparsers = parser.add_subparsers(title='commands', dest='cmd',
                                           description=SUBCOMMAND_DESCRIPTION)
        subparsers.required = False
        run_parser = subparsers.add_parser('run', help='run hotdoc')
        run_parser.add_argument('--conf-file', help='Path to the config file',
                                dest='conf_file', default='hotdoc.json')

        conf_parser = subparsers.add_parser('conf', help='configure hotdoc')
        conf_parser.add_argument('--quickstart',
                                 help='run a quickstart wizard',
                                 action='store_true')
        conf_parser.add_argument('--conf-file',
                                 help='Path to the config file',
                                 dest='conf_file', default='hotdoc.json')

        # First pass to get the conf path
        # FIXME: subparsers is useless, remove that hack
        init_args = list(args)
        split_pos = 0
        for i, arg in enumerate(init_args):
            if arg in ['run', 'conf']:
                split_pos = i
                break

        init_args = init_args[split_pos:]
        init_args = list(parser.parse_known_args(init_args))
        self.conf_file = os.path.abspath(init_args[0].conf_file)
        conf_path = os.path.dirname(self.conf_file)
        wizard = HotdocWizard(parser, conf_path=conf_path)
        self.wizard = wizard

        extension_classes = get_all_extension_classes(sort=True)

        for subclass in extension_classes:
            subclass.add_arguments(parser)
            self.extension_classes[subclass.EXTENSION_NAME] = subclass

        parser.add_argument("-i", "--index", action="store",
                            dest="index", help="location of the index file",
                            finalize_function=HotdocWizard.finalize_path)
        parser.add_argument("-o", "--output", action="store",
                            dest="output",
                            help="where to output the rendered documentation")
        parser.add_argument("--output-format", action="store",
                            dest="output_format", help="format for the output",
                            default="html")
        parser.add_argument("-I", "--include-path", action="append",
                            dest="include_paths",
                            help="markdown include paths")
        parser.add_argument("--html-theme", action="store",
                            dest="html_theme", help="html theme to use",
                            finalize_function=HotdocWizard.finalize_path)
        parser.add_argument("-", action="store_true", no_prompt=True,
                            help="Separator to allow finishing a list"
                            " of arguments before a command",
                            dest="whatever")
        parser.add_argument("--editing-server", action="store",
                            dest="editing_server", help="If editing-server"
                            " is provided, an edit button will be added")

        args = parser.parse_args(args)
        self.load_config(args, self.conf_file, wizard)

        exit_now = False

        save_config = True
        if args.cmd == 'run':
            save_config = False
            self.parse_config(wizard.config)
        elif args.cmd == 'conf':
            exit_now = True
            if args.quickstart:
                if wizard.quick_start():
                    print "Setup complete, building the documentation now"
                    if wizard.wait_for_continue(
                            "Setup complete,"
                            " press Enter to build the doc now "):
                        self.parse_config(wizard.config)
                        exit_now = False

        if save_config:
            with open(self.conf_file, 'w') as _:
                _.write(json.dumps(wizard.config, indent=4))

        if exit_now:
            sys.exit(0)

    # pylint: disable=no-self-use
    def load_config(self, args, conf_file, wizard):
        """
        Banana banana
        """
        try:
            with open(conf_file, 'r') as _:
                contents = _.read()
        except IOError:
            contents = '{}'

        try:
            config = json.loads(contents)
        except ValueError:
            config = {}

        wizard.config.update(config)
        cli = dict(vars(args))
        cli.pop('cmd', None)
        cli.pop('quickstart', None)
        cli.pop('conf_file', None)

        wizard.config.update(cli)

    def __setup_folder(self, folder):
        if os.path.exists(folder):
            if not os.path.isdir(folder):
                print "Folder %s exists but is not a directory" % folder
                raise ConfigError()
        else:
            os.mkdir(folder)

    def __create_extensions(self, args):
        for ext_class in self.extension_classes.values():
            ext = ext_class(self, args)
            self.extensions[ext.EXTENSION_NAME] = ext

    def get_private_folder(self):
        """
        Banana banana
        """
        return os.path.abspath('hotdoc-private')

    def resolve_config_path(self, path):
        """
        Banana banana
        """
        return self.wizard.resolve_config_path(path)

    def parse_config(self, config):
        """
        Banana banana
        """
        module_path = os.path.dirname(__file__)
        default_theme_path = os.path.join(module_path, '..', 'default_theme')
        default_theme_path = os.path.abspath(default_theme_path)

        self.output = config.get('output')
        self.output_format = config.get('output_format')
        self.include_paths = config.get('include_paths')
        self.html_theme_path = config.get('html_theme', default_theme_path)
        self.git_repo_path = self.resolve_config_path(config.get('git_repo'))
        self.editing_server = config.get('editing_server')

        if self.output_format not in ["html"]:
            raise ConfigError("Unsupported output format : %s" %
                              self.output_format)

        self.__load_reference_map()
        self.__create_change_tracker()

        self.__setup_folder('hotdoc-private')

        self.index_file = self.resolve_config_path(config.get('index'))

        if self.index_file is None:
            raise ConfigError("'index' is required")

        prefix = os.path.dirname(self.index_file)
        self.doc_tree = DocTree(self, prefix)

        self.__create_extensions(config)

        self.doc_tree.build_tree(self.index_file)

        moved_symbols = self.doc_tree.update_symbol_maps()

        for symbol_id in moved_symbols:
            referencing_pages = self.reference_map.get(symbol_id, set())
            for pagename in referencing_pages:
                page = self.doc_tree.pages[pagename]
                if page:
                    page.is_stale = True

        self.change_tracker.add_hard_dependency(self.conf_file)

        self.__setup_database()

    def persist(self):
        """
        Banana banana
        """
        self.doc_tree.persist()
        self.session.commit()
        self.change_tracker.track_core_dependencies()
        pickle.dump(self.change_tracker,
                    open(os.path.join(self.get_private_folder(),
                                      'change_tracker.p'), 'wb'))
        pickle.dump(self.reference_map,
                    open(os.path.join(self.get_private_folder(),
                                      'reference_map.p'), 'wb'))

    def finalize(self):
        """
        Banana banana
        """
        for extension in self.extensions.values():
            extension.finalize()
        self.persist()
        self.session.close()
