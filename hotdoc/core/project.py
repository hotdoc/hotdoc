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
import os
import io
import re
import linecache
import shutil

from collections import OrderedDict

from hotdoc.core import inclusions
from hotdoc.core.extension import Extension
from hotdoc.core.comment import Tag
from hotdoc.core.config import Config
from hotdoc.core.tree import Tree
from hotdoc.utils.loggable import info, error
from hotdoc.utils.configurable import Configurable
from hotdoc.utils.utils import OrderedSet
from hotdoc.utils.signals import Signal
from hotdoc.parsers.sitemap import SitemapParser


LANG_MAPPING = {
    'xml': 'markup',
    'html': 'markup',
    'py': 'python'
}


class CoreExtension(Extension):
    """
    Banana banana
    """
    extension_name = 'core'

    def __init__(self, app, project):
        super(CoreExtension, self).__init__(app, project)

    def format_page(self, page, link_resolver, output):
        proj = self.project.subprojects.get(page.source_file)
        if proj:
            proj.format(link_resolver, output)
            page.title = proj.tree.root.title
        else:
            return super(CoreExtension, self).format_page(
                page, link_resolver, output)

    def setup(self):
        super(CoreExtension, self).setup()
        inclusions.include_signal.disconnect(CoreExtension.include_file_cb)
        inclusions.include_signal.connect_after(CoreExtension.include_file_cb)

    def _resolve_placeholder(self, tree, fname, include_paths):
        ext = os.path.splitext(fname)[1]
        if ext != '.json':
            return None

        conf_path = inclusions.find_file(fname, include_paths)
        if not conf_path:
            error('invalid-config',
                  '(%s) Could not find subproject config file %s' % (
                      self.project.sanitized_name, fname))

        self.project.add_subproject(fname, conf_path)
        return True, None

    @staticmethod
    def include_file_cb(include_path, line_ranges, symbol):
        """
        Banana banana
        """
        lang = ''
        if include_path.endswith((".md", ".markdown")):
            lang = 'markdown'
        else:
            split = os.path.splitext(include_path)
            if len(split) == 2:
                ext = split[1].strip('.')
                lang = LANG_MAPPING.get(ext) or ext

        if line_ranges:
            res = []
            for line_range in line_ranges:
                for lineno in range(line_range[0] + 1, line_range[1] + 1):
                    line = linecache.getline(include_path, lineno)
                    if not line:
                        return None
                    res.append(line)
            return ''.join(res), lang

        with io.open(include_path, 'r', encoding='utf-8') as _:
            return _.read(), lang


# pylint: disable=too-many-instance-attributes
class Project(Configurable):
    """
    Banana banana
    """

    def __init__(self, app):
        self.app = app
        self.tree = None
        self.include_paths = None
        self.extensions = {}
        self.tag_validators = {}
        self.project_name = None
        self.project_version = None
        self.sanitized_name = None
        self.sitemap_path = None
        self.subprojects = {}
        self.extra_asset_folders = OrderedSet()
        self.extra_assets = {}

        if os.name == 'nt':
            self.datadir = os.path.join(
                os.path.dirname(__file__), '..', 'share')
        else:
            self.datadir = "/usr/share"

        self.formatted_signal = Signal()

        self.is_toplevel = False

    def register_tag_validator(self, validator):
        """
        Banana banana
        """
        self.tag_validators[validator.name] = validator

    def persist(self):
        """
        Banana banana
        """

        if self.app.dry:
            return

        self.tree.persist()
        for proj in self.subprojects.values():
            proj.persist()

    def finalize(self):
        """
        Banana banana
        """
        self.formatted_signal.clear()

    # pylint: disable=no-self-use
    def get_private_folder(self):
        """
        Banana banana
        """
        return self.app.private_folder

    def setup(self):
        """
        Banana banana
        """
        info('Setting up %s' % self.project_name, 'project')

        self.app.database.comment_updated_signal.connect(
            self.__comment_updated_cb)
        for extension in list(self.extensions.values()):
            info('Setting up %s' % extension.extension_name)
            extension.setup()
            self.app.database.flush()
        self.app.database.comment_updated_signal.disconnect(
            self.__comment_updated_cb)

        sitemap = SitemapParser().parse(self.sitemap_path)
        self.tree.parse_sitemap(sitemap)

        info("Resolving symbols", 'resolution')
        self.tree.resolve_symbols(self.app.database, self.app.link_resolver)
        self.app.database.flush()

    def format(self, link_resolver, output):
        """
        Banana banana
        """
        if not output:
            return

        self.tree.format(link_resolver, output, self.extensions)
        self.formatted_signal(self)

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group(
            'Project', 'project-related options')
        group.add_argument("--project-name", action="store",
                           dest="project_name",
                           help="Name of the documented project")
        group.add_argument("--project-version", action="store",
                           dest="project_version",
                           help="Version of the documented project")
        group.add_argument("-i", "--index", action="store",
                           dest="index", help="location of the "
                           "index file")
        group.add_argument("--sitemap", action="store",
                           dest="sitemap",
                           help="Location of the sitemap file")
        group.add_argument('--include-paths',
                           help='paths to look up included files in',
                           dest='include_paths', action='append',
                           default=[])
        group.add_argument(
            "--extra-assets",
            help="Extra asset folders to copy in the output",
            action='append', dest='extra_assets', default=[])

    def add_subproject(self, fname, conf_path):
        """Creates and adds a new subproject."""
        config = Config(conf_file=conf_path)
        proj = Project(self.app)
        proj.parse_name_from_config(config)
        proj.parse_config(config)
        proj.setup()
        self.subprojects[fname] = proj

    def __create_extensions(self):
        for ext_class in list(self.app.extension_classes.values()):
            ext = ext_class(self.app, self)
            self.extensions[ext.extension_name] = ext

    def __comment_updated_cb(self, doc_db, comment):
        self.tree.stale_comment_pages(comment)

    def parse_name_from_config(self, config):
        """
        Banana banana
        """
        self.project_name = config.get('project_name', None)
        if not self.project_name:
            error('invalid-config', 'No project name was provided')

        self.project_version = config.get('project_version', None)
        if not self.project_version:
            error('invalid-config', 'No project version was provided')

        self.sanitized_name = '%s-%s' % (re.sub(r'\W+', '-',
                                                self.project_name),
                                         self.project_version)

    # pylint: disable=arguments-differ
    def parse_config(self, config, toplevel=False):
        """Parses @config setting up @self state."""
        self.sitemap_path = config.get_path('sitemap')

        if self.sitemap_path is None:
            error('invalid-config',
                  'No sitemap was provided')

        self.include_paths = OrderedSet([])

        index_file = config.get_index()
        if index_file:
            if not os.path.exists(index_file):
                error('invalid-config',
                      'The provided index "%s" does not exist' %
                      index_file)
            self.include_paths |= OrderedSet([os.path.dirname(index_file)])

        self.include_paths |= OrderedSet(config.get_paths('include_paths'))

        self.is_toplevel = toplevel

        self.tree = Tree(self, self.app)

        self.__create_extensions()

        for extension in list(self.extensions.values()):
            if toplevel:
                extension.parse_toplevel_config(config)
            extension.parse_config(config)

        if not toplevel and config.conf_file:
            self.app.change_tracker.add_hard_dependency(config.conf_file)

        self.extra_asset_folders = OrderedSet(config.get_paths('extra_assets'))

    def __add_default_tags(self, _, comment):
        for validator in list(self.tag_validators.values()):
            if validator.default and validator.name not in comment.tags:
                comment.tags[validator.name] = \
                    Tag(name=validator.name,
                        description=validator.default)

    def __get_formatter(self, extension_name):
        """
        Banana banana
        """
        ext = self.extensions.get(extension_name)
        if ext:
            return ext.formatter
        return None

    def __write_extra_assets(self, output):
        for dest, src in self.extra_assets.items():
            dest = os.path.join(output, 'html', dest)
            destdir = os.path.dirname(dest)
            if not os.path.exists(destdir):
                os.makedirs(destdir)
            shutil.copyfile(src, dest)

    def write_out_tree(self, page, output):
        """Banana banana
        """
        subpages = OrderedDict({})
        ext = self.extensions[page.extension_name]
        subpage_names = ext.get_subpages_sorted(self.tree.get_pages(), page)
        formatter = ext.formatter
        for pagename in subpage_names:
            proj = self.subprojects.get(pagename)

            if not proj:
                cpage = self.tree.get_pages()[pagename]
                sub_formatter = self.extensions[cpage.extension_name].formatter
                self.write_out_tree(cpage, output)
            else:
                cpage = proj.tree.root
                sub_formatter = proj.extensions[cpage.extension_name].formatter
                proj.write_out_tree(cpage, output)

            subpage_link = cpage.link.get_link(self.app.link_resolver)
            prefix = sub_formatter.get_output_folder(cpage)
            if prefix:
                subpage_link = '%s/%s' % (prefix, subpage_link)
            subpages[subpage_link] = cpage

        html_subpages = formatter.format_subpages(page, subpages)
        formatter.write_out(page, html_subpages, output)

    def write_out(self, output):
        """Banana banana
        """
        ext = self.extensions.get(self.tree.root.extension_name)
        html_sitemap = ext.formatter.format_navigation(self)

        if html_sitemap:
            escaped_sitemap = html_sitemap.replace(
                '\\', '\\\\').replace('"', '\\"').replace('\n', '')
            js_wrapper = 'sitemap_downloaded_cb("%s");' % escaped_sitemap
            js_dir = os.path.join(output, 'html', 'assets', 'js')
            if not os.path.exists(js_dir):
                os.makedirs(js_dir)
            with open(os.path.join(js_dir, 'sitemap.js'), 'w') as _:
                _.write(js_wrapper)

        self.write_out_tree(self.tree.root, output)

        self.__write_extra_assets(output)
        ext.formatter.copy_assets(os.path.join(output, 'html', 'assets'))

        # Just in case the sitemap root isn't named index
        ext_folder = ext.formatter.get_output_folder(self.tree.root)
        index_path = os.path.join(
            ext_folder,
            self.tree.root.link.get_link(self.app.link_resolver))

        default_index_path = os.path.join(output, 'html', 'index.html')

        if not os.path.exists(default_index_path):
            with open(default_index_path, 'w', encoding='utf8') as _:
                _.write('<meta http-equiv="refresh" content="0; url=%s"/>' %
                        index_path)
