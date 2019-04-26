#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2016 Collabora Ltd
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

"""The main hotdoc application
"""

import argparse
import cProfile
import json
import os
import shutil
import sys
import traceback

from urllib.parse import urlparse
from collections import OrderedDict

from hotdoc.core.project import Project, CoreExtension
from hotdoc.core.config import Config, load_config_json
from hotdoc.core.exceptions import HotdocException
from hotdoc.core.database import Database
from hotdoc.core.links import LinkResolver, Link
from hotdoc.utils.utils import all_subclasses, get_extension_classes, get_cat
from hotdoc.utils.loggable import Logger, error, info
from hotdoc.utils.setup_utils import VERSION
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.signals import Signal


class Application(Configurable):
    """
    Banana banana
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, extension_classes):
        self.extension_classes = OrderedDict(
            {CoreExtension.extension_name: CoreExtension})
        for ext_class in extension_classes:
            self.extension_classes[ext_class.extension_name] = ext_class
        self.output = None
        self.private_folder = None
        self.database = None
        self.link_resolver = None
        self.dry = False
        self.hostname = None
        self.config = None
        self.project = None
        self.formatted_signal = Signal()
        self.__all_projects = {}

    @staticmethod
    def add_arguments(parser):
        parser.add_argument('--dry',
                            help='Dry run, nothing will be output',
                            dest='dry', action='store_true')
        parser.add_argument('--deps-file-dest',
                            help='Where to output the dependencies file')
        parser.add_argument('--deps-file-target',
                            help='Name of the dependencies target',
                            default='doc.stamp.d')
        parser.add_argument("-o", "--output", action="store",
                            dest="output",
                            help="where to output the rendered "
                            "documentation")
        parser.add_argument('--hostname', dest='hostname', action='store',
                            help='Where the documentation will be hosted, '
                            'for example <http://hotdoc.com>. When provided, '
                            'an XML sitemap will be generated for SEO '
                            'purposes.')

    def parse_config(self, config):
        self.config = config
        self.output = config.get_path('output')
        self.dry = config.get('dry')
        self.hostname = config.get('hostname')
        self.project = Project(self)
        self.project.parse_name_from_config(self.config)
        self.private_folder = os.path.abspath(
            'hotdoc-private-%s' % self.project.sanitized_name)
        shutil.rmtree(self.private_folder, ignore_errors=True)
        self.project.parse_config(self.config, toplevel=True)

        self.__setup_private_folder()
        self.__setup_database()

    def run(self):
        """
        Banana banana
        """
        res = 0

        self.project.setup()
        self.__retrieve_all_projects(self.project)

        self.link_resolver.get_link_signal.connect_after(self.__get_link_cb)
        self.project.format(self.link_resolver, self.output)
        self.project.write_out(self.output)

        # Generating an XML sitemap makes no sense without a hostname
        if self.hostname:
            self.project.write_seo_sitemap(self.hostname, self.output)

        self.link_resolver.get_link_signal.disconnect(self.__get_link_cb)

        self.formatted_signal(self)
        self.__persist()

        return res

    def __get_link_cb(self, link_resolver, name):
        url_components = urlparse(name)

        project = self.__all_projects.get(url_components.path)
        if not project:
            return None

        page = project.tree.root
        ext = project.extensions[page.extension_name]
        formatter = ext.formatter
        prefix = formatter.get_output_folder(page)
        ref = page.link.ref
        if url_components.fragment:
            ref += '#%s' % url_components.fragment

        return Link(os.path.join(prefix, ref), page.link.get_title(), None)

    def __retrieve_all_projects(self, project):
        self.__all_projects[project.project_name] = project

        for subproj in project.subprojects.values():
            self.__retrieve_all_projects(subproj)

    def __persist(self):
        if self.dry:
            return

        info('Persisting database and private files', 'persisting')

        self.database.persist()

    def finalize(self):
        """
        Banana banana
        """
        self.project.finalize()

    def __setup_private_folder(self):
        if os.path.exists(self.private_folder):
            if not os.path.isdir(self.private_folder):
                error('setup-issue',
                      '%s exists but is not a directory' % self.private_folder)
        else:
            os.mkdir(self.private_folder)

    def __setup_database(self):
        self.database = Database(self.private_folder)
        self.link_resolver = LinkResolver(self.database)


def check_path(init_dir, name):
    """
    Banana banana
    """
    path = os.path.join(init_dir, name)
    if os.path.exists(path):
        error('setup-issue', '%s already exists' % path)
    return path


def create_default_layout(config):
    """
    Banana banana
    """
    project_name = config.get('project_name')
    project_version = config.get('project_version')

    if not project_name or not project_version:
        error('setup-issue',
              '--project-name and --project-version must be specified')

    init_dir = config.get_path('init_dir')
    if not init_dir:
        init_dir = config.get_invoke_dir()
    else:
        if os.path.exists(init_dir) and not os.path.isdir(init_dir):
            error('setup-issue',
                  'Init directory exists but is not a directory: %s' %
                  init_dir)

    sitemap_path = check_path(init_dir, 'sitemap.txt')
    conf_path = check_path(init_dir, 'hotdoc.json')
    md_folder_path = check_path(init_dir, 'markdown_files')
    assets_folder_path = check_path(init_dir, 'assets')
    check_path(init_dir, 'built_doc')
    cat_path = os.path.join(assets_folder_path, 'cat.gif')

    os.makedirs(init_dir)
    os.makedirs(assets_folder_path)
    os.makedirs(md_folder_path)

    with open(sitemap_path, 'w') as _:
        _.write('index.md\n')

    with open(conf_path, 'w') as _:
        _.write(json.dumps({'project_name': project_name,
                            'project_version': project_version,
                            'sitemap': 'sitemap.txt',
                            'index': os.path.join('markdown_files',
                                                  'index.md'),
                            'output': 'built_doc',
                            'extra_assets': ['assets']}, indent=4))

    with open(os.path.join(md_folder_path, 'index.md'), 'w') as _:
        _.write('# %s\n' % project_name.capitalize())
        try:
            get_cat(cat_path)
            _.write("\nIt's dangerous to go alone, take this\n")
            _.write('\n![](assets/cat.gif)')
        except:  # pylint: disable=bare-except
            pass


# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
def execute_command(parser, config, ext_classes):
    """
    Banana banana
    """
    res = 0
    cmd = config.get('command')

    get_private_folder = config.get('get_private_folder', False)

    if cmd == 'help':
        parser.print_help()
    elif cmd == 'run' or get_private_folder:  # git.mk backward compat
        app = Application(ext_classes)
        try:
            app.parse_config(config)
            if get_private_folder:
                print(app.private_folder)
                return res
            res = app.run()
        except HotdocException:
            res = len(Logger.get_issues())
        except Exception:  # pylint: disable=broad-except
            print("An unknown error happened while building the documentation"
                  " and hotdoc cannot recover from it. Please report "
                  "a bug with this error message and the steps to "
                  "reproduce it")
            traceback.print_exc()
            res = 1
        finally:
            app.finalize()
    elif cmd == 'init':
        try:
            create_default_layout(config)
        except HotdocException:
            res = 1
    elif cmd == 'conf':
        config.dump(conf_file=config.get('output_conf_file', None))
    elif cmd is None:
        if config.get('version'):
            print(VERSION)
        elif config.get('makefile_path'):
            here = os.path.dirname(__file__)
            path = os.path.join(here, 'utils', 'hotdoc.mk')
            print(os.path.abspath(path))
        elif config.get('get_conf_path'):
            key = config.get('get_conf_path')
            path = config.get_path(key, rel_to_cwd=True)
            if path is not None:
                print(path)
        elif config.get('get_conf_key'):
            key = config.get('get_conf_key')
            value = config.get(key, None)
            if value is not None:
                print(value)
        else:
            parser.print_usage()
    else:
        parser.print_usage()

    return res


# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
def run(args, verbose=False):
    """
    Banana banana
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False)
    parser.add_argument("--extra-extension-path", action="append",
                        default=[],
                        dest="extra_extension_path",
                        help="An extra extension path to use")
    parser.add_argument('--conf-file', help='Path to the config file',
                        dest='conf_file')
    tmpargs, _args = parser.parse_known_args(args)

    json_conf = None
    if tmpargs.conf_file:
        json_conf = load_config_json(tmpargs.conf_file)
        tmpargs.extra_extension_path += json_conf.get('extra_extension_path',
                                                      [])

    # We only get these once, doing this now means all
    # installed extensions will show up as Configurable subclasses.
    try:
        ext_classes = get_extension_classes(
            sort=True, extra_extension_paths=tmpargs.extra_extension_path)
    except HotdocException:
        return 1

    parser.add_argument('command', action="store",
                        choices=('run', 'conf', 'init', 'help'),
                        nargs="?")
    parser.add_argument('--output-conf-file',
                        help='Path where to save the updated conf'
                        ' file',
                        dest='output_conf_file')
    parser.add_argument('--init-dir',
                        help='Directory to initialize',
                        dest='init_dir')
    parser.add_argument('--version', help="Print version and exit",
                        action="store_true")
    parser.add_argument('--makefile-path',
                        help="Print path to includable "
                        "Makefile and exit",
                        action="store_true")
    parser.add_argument("--get-conf-key", action="store",
                        help="print the value for a configuration "
                        "key")
    parser.add_argument("--get-conf-path", action="store",
                        help="print the value for a configuration "
                        "path")
    parser.add_argument("--get-private-folder", action="store_true",
                        help="get the path to hotdoc's private "
                        "folder")
    parser.add_argument("--has-extension", action="append",
                        dest="has_extensions", default=[],
                        help="Check if a given extension is available")
    parser.add_argument("--list-extensions", action="store_true",
                        dest="list_extensions", help="Print "
                        "available extensions")
    parser.add_argument("-", action="store_true",
                        help="Separator to allow finishing a list"
                        " of arguments before a command",
                        dest="whatever")

    add_args_methods = set()

    for klass in all_subclasses(Configurable):
        if klass.add_arguments not in add_args_methods:
            klass.add_arguments(parser)
            add_args_methods.add(klass.add_arguments)

    known_args, _ = parser.parse_known_args(args)

    defaults = {}
    actual_args = {}
    for key, value in list(dict(vars(known_args)).items()):
        if value != parser.get_default(key):
            actual_args[key] = value
        if parser.get_default(key) is not None:
            defaults[key] = value

    if known_args.has_extensions:
        res = 0
        for extension_name in known_args.has_extensions:
            found = False
            for klass in ext_classes:
                if klass.extension_name == extension_name:
                    found = True
                    if verbose:
                        print("Extension '%s'... FOUND." % extension_name)
            if not found:
                if verbose:
                    print("Extension '%s'... NOT FOUND." % extension_name)
                res = 1
        return res

    if known_args.list_extensions:
        print("Extensions:")
        extensions = [e.extension_name for e in ext_classes]
        for extension in sorted(extensions):
            print(" - %s " % extension)
        return 0

    if known_args.command != 'init':
        conf_file = actual_args.get('conf_file')
        if conf_file is None and os.path.exists('hotdoc.json'):
            conf_file = 'hotdoc.json'
    else:
        conf_file = ''

    config = Config(command_line_args=actual_args,
                    conf_file=conf_file,
                    defaults=defaults,
                    json_conf=json_conf)

    Logger.parse_config(config)

    return execute_command(parser, config, ext_classes)


def main():
    run_profile = os.environ.get('HOTDOC_PROFILING', False)
    res = 0

    if run_profile:
        prof = cProfile.Profile()
        res = prof.runcall(run, sys.argv[1:], verbose=True)
        prof.dump_stats('hotdoc-runstats')
    else:
        res = run(sys.argv[1:], verbose=True)

    return res
