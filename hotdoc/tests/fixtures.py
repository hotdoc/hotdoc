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

# pylint: disable=missing-docstring

import unittest
import os
import json
import shutil

from hotdoc.core.config import Config
from hotdoc.utils.utils import touch
from hotdoc.utils.utils import get_extension_classes
from hotdoc.run_hotdoc import Application
from hotdoc.core.database import Database
from hotdoc.core.links import LinkResolver
from hotdoc.core.tree import Tree


# pylint: disable=too-many-instance-attributes
class HotdocTest(unittest.TestCase):

    def setUp(self):
        self._here = os.path.dirname(__file__)
        self._md_dir = os.path.abspath(os.path.join(
            self._here, 'tmp-markdown-files'))
        self.private_folder = os.path.abspath(os.path.join(
            self._here, 'tmp-private'))
        self._src_dir = os.path.abspath(os.path.join(
            self._here, 'tmp-src-files'))
        self._output_dir = os.path.abspath(os.path.join(
            self._here, 'tmp-output'))
        self._remove_tmp_dirs()
        os.mkdir(self._md_dir)
        os.mkdir(self.private_folder)
        os.mkdir(self._src_dir)
        self.dependency_map = {}
        self.database = Database(self.private_folder)
        self.link_resolver = LinkResolver(self.database)
        self.sanitized_name = 'test-project-0.1'
        self.tree = Tree(self, self)

    def tearDown(self):
        self._remove_tmp_dirs()

    def _remove_tmp_dirs(self):
        shutil.rmtree(self._md_dir, ignore_errors=True)
        shutil.rmtree(self.private_folder, ignore_errors=True)
        shutil.rmtree(self._src_dir, ignore_errors=True)
        shutil.rmtree(self._output_dir, ignore_errors=True)

    def _create_md_file(self, name, contents):
        path = os.path.join(self._md_dir, name)
        try:
            os.mkdir(os.path.dirname(path))
        except FileExistsError:
            pass
        with open(path, 'w') as _:
            _.write(contents)

        touch(path)
        return path

    def _create_sitemap(self, name, contents):
        path = os.path.join(self._md_dir, name)
        with open(path, 'w') as _:
            _.write(contents)

        touch(path)
        return path

    def _create_conf_file(self, name, conf):
        path = os.path.join(self._md_dir, name)
        with open(path, 'w') as _:
            _.write(json.dumps(conf, indent=4))

        touch(path)
        return path

    def _create_src_file(self, name, symbols):
        path = os.path.join(self._src_dir, name)
        with open(path, 'w') as _:
            for symbol in symbols:
                _.write('%s\n' % symbol)

        # Just making sure we don't hit a race condition,
        # in real world situations it is assumed users
        # will not update source files twice in the same
        # microsecond
        touch(path)
        return path

    def _create_project_config_file(self, name, version='0.2',
                                    sitemap_content=None,
                                    extra_conf=None):
        sitemap_name = name + '.txt'
        index_name = name + '.markdown'
        config_name = name + '.json'

        if not sitemap_content:
            sitemap_content = index_name
        sm_path = self._create_sitemap(sitemap_name, sitemap_content)

        index_content = "#" + name[0].upper() + name[1:]
        index_path = self._create_md_file(index_name, index_content)

        conf = {'index': index_path, 'sitemap': sm_path,
                'project_name': name, 'project_version': version,
                'output': self._output_dir}

        if extra_conf:
            conf.update(extra_conf)

        return self._create_conf_file(config_name, conf)

    def _create_project_config(self, name, **kwargs):
        return Config(conf_file=self._create_project_config_file(name,
                                                                 **kwargs))

    @staticmethod
    def create_application():
        ext_classes = get_extension_classes(sort=True)

        return Application(ext_classes)
