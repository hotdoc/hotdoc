# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""
Core of the core.
"""

import argparse
import cPickle as pickle
import json
import os
import shutil
import sys
import io

from hotdoc.core import file_includer
from hotdoc.core.base_extension import BaseExtension
from hotdoc.core.base_formatter import Formatter
from hotdoc.core.change_tracker import ChangeTracker
from hotdoc.core.comment_block import Tag
from hotdoc.core.doc_database import DocDatabase
from hotdoc.core.doc_tree import DocTree
from hotdoc.core.links import LinkResolver
from hotdoc.core.wizard import HotdocWizard
from hotdoc.utils.loggable import info, error
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.utils import get_all_extension_classes, all_subclasses
from hotdoc.utils.utils import OrderedSet


SUBCOMMAND_DESCRIPTION = """
Valid subcommands.

Exactly one subcommand is required.
Run hotdoc {subcommand} -h for more info
"""


class CoreExtension(BaseExtension):
    """
    Banana banana
    """
    EXTENSION_NAME = 'core'

    def __init__(self, doc_repo):
        super(CoreExtension, self).__init__(doc_repo)
        file_includer.include_signal.connect_after(self.__include_file_cb)

    # pylint: disable=no-self-use
    def __include_file_cb(self, include_path, line_ranges, symbol):
        lang = ''
        if include_path.endswith((".md", ".markdown")):
            lang = 'markdown'

        with io.open(include_path, 'r', encoding='utf-8') as _:
            return _.read(), lang


class DocRepo(object):
    """
    Banana banana
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.output = None
        self.wizard = None
        self.doc_tree = None
        self.git_repo_path = None
        self.change_tracker = None
        self.output_format = None
        self.include_paths = None
        self.extensions = {}
        self.tag_validators = {}
        self.link_resolver = None
        self.incremental = False
        self.doc_database = None

        if os.name == 'nt':
            self.datadir = os.path.join(
                os.path.dirname(__file__), '..', 'share')
        else:
            self.datadir = "/usr/share"

        self.__conf_file = None
        self.__extension_classes = {
            CoreExtension.EXTENSION_NAME: CoreExtension}
        self.__index_file = None
        self.__root_page = None

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
        pages = self.doc_tree.get_pages_for_symbol(symbol_name)
        if not pages:
            return None

        page = pages.values()[0]

        formatter = self.__get_formatter(page.extension_name)

        sym = self.doc_database.get_symbol(symbol_name)
        if not sym:
            return None

        sym.update_children_comments()
        old_server = Formatter.editing_server
        Formatter.editing_server = None
        formatter.format_symbol(sym, self.link_resolver)
        Formatter.editing_server = old_server

        return sym.detailed_description

    def patch_page(self, symbol, raw_comment):
        """
        Banana banana
        """
        pages = self.doc_tree.get_pages_for_symbol(symbol.unique_name)
        if not pages:
            return False

        old_comment = symbol.comment
        # pylint: disable=no-member
        new_comment = self.raw_comment_parser.parse_comment(
            raw_comment,
            old_comment.filename,
            old_comment.lineno,
            old_comment.lineno + raw_comment.count('\n'),
            self.include_paths)

        if new_comment is None:
            return False

        if new_comment.name != symbol.unique_name:
            return False

        pages = pages.values()
        symbol.comment = new_comment
        for page in pages:
            formatter = self.__get_formatter(page.extension_name)
            formatter.patch_page(page, symbol, self.output)

        return True

    def persist(self):
        """
        Banana banana
        """
        info('Persisting database and private files', 'persisting')
        self.doc_tree.persist()
        self.doc_database.persist()
        self.change_tracker.track_core_dependencies()
        pickle.dump(self.change_tracker,
                    open(os.path.join(self.get_private_folder(),
                                      'change_tracker.p'), 'wb'))

    def finalize(self):
        """
        Banana banana
        """
        for extension in self.extensions.values():
            info('Finalizing %s' % extension.EXTENSION_NAME)
            extension.finalize()
        info('Closing database')
        self.doc_database.finalize()

    # pylint: disable=no-self-use
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

    def setup(self, args):
        """
        Banana banana
        """
        self.__setup(args)

        for extension in self.extensions.values():
            info('Setting up %s' % extension.EXTENSION_NAME)
            extension.setup()
            self.doc_database.flush()

        info("Resolving symbols", 'resolution')
        self.doc_tree.resolve_symbols(self.doc_database, self.link_resolver,
                                      self.__root_page)
        self.doc_database.flush()

    def format(self):
        """
        Banana banana
        """
        self.doc_tree.format(self.link_resolver, self.output, self.extensions)

    def __add_default_tags(self, _, comment):
        for validator in self.tag_validators.values():
            if validator.default and validator.name not in comment.tags:
                comment.tags[validator.name] = \
                    Tag(name=validator.name,
                        description=validator.default)

    def __setup_database(self):
        self.doc_database = DocDatabase()
        self.doc_database.comment_added_signal.connect(self.__add_default_tags)
        self.doc_database.comment_updated_signal.connect(
            self.__add_default_tags)
        self.doc_database.setup(self.get_private_folder())
        self.link_resolver = LinkResolver(self.doc_database)

    def __create_change_tracker(self):
        try:
            self.change_tracker = \
                pickle.load(open(os.path.join(self.get_private_folder(),
                                              'change_tracker.p'), 'rb'))
            if self.change_tracker.hard_dependencies_are_stale():
                raise IOError
            self.incremental = True
            info("Building incrementally")
        # pylint: disable=broad-except
        except Exception:
            info("Building from scratch")
            shutil.rmtree(self.get_private_folder(), ignore_errors=True)
            shutil.rmtree(self.output, ignore_errors=True)
            gen_folder = self.get_generated_doc_folder()
            shutil.rmtree(gen_folder, ignore_errors=True)
            self.change_tracker = ChangeTracker()

    def __get_formatter(self, extension_name):
        """
        Banana banana
        """
        ext = self.extensions.get(extension_name)
        if ext:
            return ext.get_formatter(self.output_format)
        return None

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches
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

        help_parser = subparsers.add_parser('help', help='print hotdoc help')
        help_parser.add_argument('--conf-file', help='Path to the config file',
                                 dest='conf_file', default='hotdoc.json')

        conf_parser = subparsers.add_parser('conf', help='configure hotdoc')
        conf_parser.add_argument('--quickstart',
                                 help='run a quickstart wizard',
                                 action='store_true')
        conf_parser.add_argument('--conf-file',
                                 help='Path to the config file',
                                 dest='conf_file', default='hotdoc.json')

        cmd = self.__setup_config_file(parser, args)
        conf_path = os.path.dirname(self.__conf_file)
        wizard = HotdocWizard(parser, conf_path=conf_path)
        self.wizard = wizard

        extension_classes = get_all_extension_classes(sort=True)
        for subclass in extension_classes:
            self.__extension_classes[subclass.EXTENSION_NAME] = subclass

        configurable_classes = all_subclasses(Configurable)

        seen = set()
        for subclass in configurable_classes:
            if subclass.add_arguments not in seen:
                subclass.add_arguments(parser)
                seen.add(subclass.add_arguments)

        parser.add_argument("-i", "--index", action="store",
                            dest="index", help="location of the index file",
                            finalize_function=HotdocWizard.finalize_path)
        parser.add_argument("-o", "--output", action="store",
                            dest="output",
                            help="where to output the rendered documentation")
        parser.add_argument("--output-format", action="store",
                            dest="output_format", help="format for the output",
                            default="html")
        parser.add_argument("-", action="store_true", no_prompt=True,
                            help="Separator to allow finishing a list"
                            " of arguments before a command",
                            dest="whatever")

        if cmd == 'help':
            parser.print_help()
            sys.exit(0)

        args = parser.parse_args(args)
        self.__load_config(args, self.__conf_file, wizard)

        configured = set()
        for subclass in configurable_classes:
            if subclass.parse_config not in configured:
                subclass.parse_config(self, wizard.config)
                configured.add(subclass.parse_config)

        exit_now = False
        save_config = True

        if args.cmd == 'run':
            save_config = False
            self.__parse_config(wizard.config)
        elif args.cmd == 'conf':
            exit_now = True
            if args.quickstart:
                exit_now = self.__quickstart(wizard)
        elif args.cmd == 'help':
            exit_now = True
            save_config = False

        if save_config:
            with open(self.__conf_file, 'w') as _:
                _.write(json.dumps(wizard.config, indent=4))

        if exit_now:
            sys.exit(0)

    def __quickstart(self, wizard):
        exit_now = True
        if wizard.quick_start():
            info("Setup complete, building the documentation now")
            try:
                wizard.wait_for_continue(
                    "Setup complete,"
                    " press Enter to build the doc now ")
                self.__parse_config(wizard.config)
                exit_now = False
            except EOFError:
                pass
        return exit_now

    def __setup_config_file(self, parser, args):
        # First pass to get the conf path
        # FIXME: subparsers is useless, remove that hack
        init_args = list(args)
        split_pos = 0
        cmd = None
        for i, arg in enumerate(init_args):
            if arg in ['run', 'conf', 'help']:
                cmd = arg
                split_pos = i
                break

        init_args = init_args[split_pos:]
        init_args = list(parser.parse_known_args(init_args))
        self.__conf_file = os.path.abspath(init_args[0].conf_file)

        return cmd

    # pylint: disable=no-self-use
    def __load_config(self, args, conf_file, wizard):
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
                error('setup-issue',
                      'Folder %s exists but is not a directory' % folder)
        else:
            os.mkdir(folder)

    def __create_extensions(self):
        for ext_class in self.__extension_classes.values():
            ext = ext_class(self)
            self.extensions[ext.EXTENSION_NAME] = ext

    def get_base_doc_folder(self):
        """Get the folder in which the main index was located
        """
        return next(iter(self.include_paths))

    def get_generated_doc_folder(self):
        """Get the folder in which auto-generated doc pages
        are to be output
        """
        return os.path.join(self.get_private_folder(), 'generated')

    def __parse_config(self, config):
        """
        Banana banana
        """
        self.output = config.get('output')
        if not self.output:
            error('invalid-config', 'output has to be specified')
        self.output_format = config.get('output_format')

        if self.output_format not in ["html"]:
            error('invalid-config',
                  'Unsupported output format : %s' % self.output_format)

        self.__index_file = self.resolve_config_path(config.get('index'))
        if self.__index_file is None:
            error('invalid-config', 'index is required')
        if not os.path.exists(self.__index_file):
            error('invalid-config',
                  'The provided index "%s" does not exist' %
                  self.__index_file)

        cmd_line_includes = [self.resolve_config_path(path) for path in
                             config.get('include_paths', [])]
        base_doc_path = os.path.dirname(self.__index_file)
        gen_folder = self.get_generated_doc_folder()
        self.include_paths = OrderedSet([gen_folder])
        self.include_paths.add(base_doc_path)
        self.include_paths |= OrderedSet(cmd_line_includes)
        self.git_repo_path = self.resolve_config_path(config.get('git_repo'))
        self.__create_change_tracker()
        self.__setup_folder('hotdoc-private')
        self.__setup_database()

        if not os.path.exists(gen_folder):
            os.makedirs(gen_folder)

        self.doc_tree = DocTree(self.include_paths, self.get_private_folder())

        self.__create_extensions()

        info('Building documentation tree')
        self.__root_page = self.doc_tree.build_tree(self.__index_file, 'core')

        self.change_tracker.add_hard_dependency(self.__conf_file)
