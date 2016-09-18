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
import hashlib
import cPickle as pickle
import os
import shutil
import sys
import io

from hotdoc.core import file_includer
from hotdoc.core.base_extension import BaseExtension
from hotdoc.core.change_tracker import ChangeTracker
from hotdoc.core.comment_block import Tag
from hotdoc.core.config import ConfigParser
from hotdoc.core.doc_database import DocDatabase
from hotdoc.core.doc_tree import DocTree
from hotdoc.core.links import LinkResolver
from hotdoc.utils.setup_utils import VERSION
from hotdoc.utils.loggable import info, error
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.utils import get_all_extension_classes, all_subclasses
from hotdoc.utils.utils import OrderedSet
from hotdoc.utils.simple_signals import Signal
from hotdoc.parsers.standalone_parser import SitemapParser


SUBCOMMAND_DESCRIPTION = """
Valid subcommands.

Exactly one subcommand is required.
Run hotdoc {subcommand} -h for more info
"""


LANG_MAPPING = {
    'xml': 'markup',
    'html': 'markup',
    'py': 'python'
}


class CoreExtension(BaseExtension):
    """
    Banana banana
    """
    extension_name = 'core'

    def __init__(self, doc_repo):
        super(CoreExtension, self).__init__(doc_repo)
        file_includer.include_signal.connect_after(self.__include_file_cb)

    # pylint: disable=no-self-use
    def __include_file_cb(self, include_path, line_ranges, symbol):
        lang = ''
        if include_path.endswith((".md", ".markdown")):
            lang = 'markdown'
        else:
            split = os.path.splitext(include_path)
            if len(split) == 2:
                ext = split[1].strip('.')
                lang = LANG_MAPPING.get(ext) or ext

        with io.open(include_path, 'r', encoding='utf-8') as _:
            return _.read(), lang


# pylint: disable=too-many-instance-attributes
class DocRepo(object):
    """
    Banana banana
    """

    formatted_signal = Signal()

    def __init__(self):
        self.output = None
        self.doc_tree = None
        self.change_tracker = None
        self.output_format = None
        self.include_paths = None
        self.extensions = {}
        self.tag_validators = {}
        self.link_resolver = None
        self.incremental = False
        self.doc_database = None
        self.config = None
        self.project_name = None
        self.project_version = None
        self.sitemap_path = None

        if os.name == 'nt':
            self.datadir = os.path.join(
                os.path.dirname(__file__), '..', 'share')
        else:
            self.datadir = "/usr/share"

        self.__conf_file = None
        self.__extension_classes = {
            CoreExtension.extension_name: CoreExtension}
        self.__index_file = None
        self.__root_page = None
        self.__base_doc_folder = None
        self.__private_folder = None
        self.__dry = False
        self.__load_extensions()
        self.__create_arg_parser()

    def register_tag_validator(self, validator):
        """
        Banana banana
        """
        self.tag_validators[validator.name] = validator

    def format_symbol(self, symbol_name):
        """
        Banana banana
        """
        sym = self.doc_database.get_symbol(symbol_name)
        if not sym:
            return None

        sym.update_children_comments()

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

        if self.__dry:
            return

        info('Persisting database and private files', 'persisting')
        self.doc_tree.persist()
        self.doc_database.persist()
        pickle.dump(self.change_tracker,
                    open(os.path.join(self.get_private_folder(),
                                      'change_tracker.p'), 'wb'))

        self.__dump_deps_file()

    def finalize(self):
        """
        Banana banana
        """
        self.formatted_signal.clear()
        if self.doc_database is not None:
            info('Closing database')
            self.doc_database.close()

    # pylint: disable=no-self-use
    def get_private_folder(self):
        """
        Banana banana
        """
        return self.__private_folder

    def setup(self):
        """
        Banana banana
        """
        configurable_classes = all_subclasses(Configurable)

        configured = set()
        for subclass in configurable_classes:
            if subclass.parse_config not in configured:
                subclass.parse_config(self, self.config)
                configured.add(subclass.parse_config)
        self.__parse_config()

        self.doc_tree = DocTree(self.get_private_folder(), self.include_paths)

        for extension in self.extensions.values():
            info('Setting up %s' % extension.extension_name)
            extension.setup()
            self.doc_database.flush()

        sitemap = SitemapParser().parse(self.sitemap_path)
        self.doc_tree.parse_sitemap(self.change_tracker, sitemap)

        info("Resolving symbols", 'resolution')
        self.doc_tree.resolve_symbols(self.doc_database, self.link_resolver)
        self.doc_database.flush()

    def format(self):
        """
        Banana banana
        """
        if not self.output:
            return

        self.doc_tree.format(self.link_resolver, self.output, self.extensions)
        self.config.dump(conf_file=os.path.join(self.output, 'hotdoc.json'))
        self.formatted_signal(self)

    def __dump_deps_file(self):
        dest = self.config.get('deps_file_dest')
        target = self.config.get('deps_file_target')

        if dest is None:
            info("Not dumping deps file")
            return

        info("Dumping deps file to %s with target %s" % (dest, target))
        destdir = os.path.dirname(dest)
        if not os.path.exists(destdir):
            os.makedirs(destdir)

        empty_targets = []

        with io.open(dest, 'w', encoding='utf-8') as _:
            _.write(u'%s: ' % target)

            if self.config:
                for dep in self.config.get_dependencies():
                    empty_targets.append(dep)
                    _.write(u'%s ' % dep)

            if self.doc_tree:
                for page in self.doc_tree.get_pages().values():
                    if not page.generated:
                        empty_targets.append(page.source_file)
                        _.write(u'%s ' % page.source_file)

            for empty_target in empty_targets:
                _.write(u'\n\n%s:' % empty_target)

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
            if self.output:
                shutil.rmtree(self.output, ignore_errors=True)
            self.change_tracker = ChangeTracker()

    def __get_formatter(self, extension_name):
        """
        Banana banana
        """
        ext = self.extensions.get(extension_name)
        if ext:
            return ext.get_formatter(self.output_format)
        return None

    def __check_initial_args(self, args):
        if args.version:
            print VERSION
        elif args.makefile_path:
            here = os.path.dirname(__file__)
            path = os.path.join(here, '..', 'utils', 'hotdoc.mk')
            print os.path.abspath(path)
        elif args.get_conf_path:
            key = args.get_conf_path
            path = self.config.get_path(key, rel_to_cwd=True)
            if path is not None:
                print path
        elif args.get_conf_key:
            key = args.get_conf_key
            value = self.config.get(args.get_conf_key, None)
            if value is not None:
                print value
        elif args.get_private_folder:
            print os.path.relpath(self.__private_folder,
                                  self.config.get_invoke_dir())
        elif args.has_extension:
            ext_name = args.has_extension
            print ext_name in self.__extension_classes
        elif args.list_extensions:
            for ext_name in self.__extension_classes:
                print ext_name
        else:
            self.parser.print_usage()

    def __create_arg_parser(self):
        self.parser = \
            argparse.ArgumentParser(
                formatter_class=argparse.RawDescriptionHelpFormatter,)

        configurable_classes = all_subclasses(Configurable)

        seen = set()
        for subclass in configurable_classes:
            if subclass.add_arguments not in seen:
                subclass.add_arguments(self.parser)
                seen.add(subclass.add_arguments)

        self.parser.add_argument('command', action="store",
                                 choices=('run', 'conf', 'help'),
                                 nargs="?")
        self.parser.add_argument('--dry',
                                 help='Dry run, nothing will be output',
                                 dest='dry', action='store_true')
        self.parser.add_argument('--conf-file', help='Path to the config file',
                                 dest='conf_file')
        self.parser.add_argument('--output-conf-file',
                                 help='Path where to save the updated conf'
                                 ' file',
                                 dest='output_conf_file')
        self.parser.add_argument('--version', help="Print version and exit",
                                 action="store_true")
        self.parser.add_argument('--makefile-path',
                                 help="Print path to includable "
                                 "Makefile and exit",
                                 action="store_true")
        self.parser.add_argument('--deps-file-dest',
                                 help='Where to output the dependencies file')
        self.parser.add_argument('--deps-file-target',
                                 help='Name of the dependencies target',
                                 default='doc.stamp.d')
        self.parser.add_argument("-i", "--index", action="store",
                                 dest="index", help="location of the "
                                 "index file")
        self.parser.add_argument("--sitemap", action="store",
                                 dest="sitemap",
                                 help="Location of the sitemap file")
        self.parser.add_argument("--project-name", action="store",
                                 dest="project_name",
                                 help="Name of the documented project")
        self.parser.add_argument("--project-version", action="store",
                                 dest="project_version",
                                 help="Version of the documented project")
        self.parser.add_argument("-o", "--output", action="store",
                                 dest="output",
                                 help="where to output the rendered "
                                 "documentation")
        self.parser.add_argument("--get-conf-key", action="store",
                                 help="print the value for a configuration "
                                 "key")
        self.parser.add_argument("--get-conf-path", action="store",
                                 help="print the value for a configuration "
                                 "path")
        self.parser.add_argument("--get-private-folder", action="store_true",
                                 help="get the path to hotdoc's private "
                                 "folder")
        self.parser.add_argument("--output-format", action="store",
                                 dest="output_format", help="format for the "
                                 "output")
        self.parser.add_argument("--has-extension", action="store",
                                 dest="has_extension", help="Check if a given "
                                 "extension is available")
        self.parser.add_argument("--list-extensions", action="store_true",
                                 dest="list_extensions", help="Print "
                                 "available extensions")
        self.parser.add_argument("-", action="store_true",
                                 help="Separator to allow finishing a list"
                                 " of arguments before a command",
                                 dest="whatever")

    def load_command_line(self, args):
        """
        Loads the repo from command line arguments
        """
        args = self.parser.parse_args(args)
        self.__load_config(args)

        cmd = args.command

        if cmd == 'help':
            self.parser.print_help()
            sys.exit(0)
        elif cmd is None:
            self.__check_initial_args(args)
            sys.exit(0)

        exit_now = False
        save_config = False

        if cmd == 'run':
            self.__dry = bool(args.dry)
        elif cmd == 'conf':
            save_config = True
            exit_now = True

        if save_config:
            self.config.dump(args.output_conf_file)

        if exit_now:
            sys.exit(0)

    def load_conf_file(self, conf_file, overrides):
        """
        Load the project from a configuration file and key-value
        overides.
        """
        if conf_file is None and os.path.exists('hotdoc.json'):
            conf_file = 'hotdoc.json'

        self.__conf_file = conf_file

        if conf_file and not os.path.exists(conf_file):
            error('invalid-config',
                  "No configuration file was found at %s" % conf_file)

        actual_args = {}
        defaults = {'output_format': 'html'}

        for key, value in overrides.items():
            if key in ('cmd', 'conf_file', 'dry'):
                continue
            if value != self.parser.get_default(key):
                actual_args[key] = value
            if self.parser.get_default(key) is not None:
                defaults[key] = value

        self.config = ConfigParser(command_line_args=actual_args,
                                   conf_file=conf_file,
                                   defaults=defaults)

        index = self.config.get_index()

        if index:
            hash_obj = hashlib.md5(self.config.get_index())
            priv_name = 'hotdoc-private-' + hash_obj.hexdigest()
        else:
            priv_name = 'hotdoc-private'

        self.__private_folder = os.path.abspath(priv_name)

    def __load_extensions(self):
        extension_classes = get_all_extension_classes(sort=True)
        for subclass in extension_classes:
            self.__extension_classes[subclass.extension_name] = subclass

    # pylint: disable=no-self-use
    def __load_config(self, args):
        """
        Banana banana
        """
        cli = dict(vars(args))
        self.load_conf_file(args.conf_file, cli)

    def __setup_private_folder(self):
        folder = self.get_private_folder()
        if os.path.exists(folder):
            if not os.path.isdir(folder):
                error('setup-issue',
                      '%s exists but is not a directory' % folder)
        else:
            os.mkdir(folder)

    def __create_extensions(self):
        for ext_class in self.__extension_classes.values():
            ext = ext_class(self)
            self.extensions[ext.extension_name] = ext

    def get_base_doc_folder(self):
        """Get the folder in which the main index was located
        """
        return self.__base_doc_folder

    def __parse_config(self):
        """
        Banana banana
        """
        output = self.config.get_path('output') or None
        self.sitemap_path = self.config.get_path('sitemap')

        if self.sitemap_path is None:
            error('invalid-config',
                  'No sitemap was provided')

        if output is not None:
            self.output = os.path.abspath(output)
        else:
            self.output = None

        self.project_name = self.config.get('project_name', None)
        self.project_version = self.config.get('project_version', None)
        self.output_format = self.config.get('output_format')

        if self.output_format not in ["html"]:
            error('invalid-config',
                  'Unsupported output format : %s' % self.output_format)

        self.__index_file = self.config.get_index()
        if self.__index_file is None:
            error('invalid-config', 'index is required')
        if not os.path.exists(self.__index_file):
            error('invalid-config',
                  'The provided index "%s" does not exist' %
                  self.__index_file)

        cmd_line_includes = self.config.get_paths('include_paths')
        self.__base_doc_folder = os.path.dirname(self.__index_file)
        self.include_paths = OrderedSet([self.__base_doc_folder])
        self.include_paths |= OrderedSet(cmd_line_includes)
        self.__create_change_tracker()
        self.__setup_private_folder()
        self.__setup_database()

        self.__create_extensions()

        if self.__conf_file:
            self.change_tracker.add_hard_dependency(self.__conf_file)
