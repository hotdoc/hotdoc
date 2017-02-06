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
# pylint: disable=invalid-name
# pylint: disable=no-self-use
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes
from hotdoc.tests.fixtures import HotdocTest
from hotdoc.core.exceptions import ConfigError
from hotdoc.core.project import Project, CoreExtension
from hotdoc.core.config import Config
from hotdoc.utils.loggable import Logger

class TestProject(HotdocTest):
    def setUp(self):
        super(TestProject, self).setUp()
        self.extension_classes = {CoreExtension.extension_name: CoreExtension}
        self.private_folder = self._priv_dir
        self.output = self._output_dir
        Logger.silent = True

    def test_basic(self):
        proj = Project(self)

        conf = Config({})
        with self.assertRaises(ConfigError):
            proj.parse_config(conf)

        sm_path = self._create_sitemap('sitemap.txt', 'index.markdown\n')
        conf = Config({'sitemap': sm_path})
        with self.assertRaises(ConfigError):
            proj.parse_config(conf)

        index_path = self._create_md_file('index.markdown', '# Project')
        conf = Config({'sitemap': sm_path,
                       'index': index_path,
                       'project_name': 'test-project',
                       'project_version': '0.1'})
        proj.parse_config(conf)

        self.assertDictEqual({key: type(val) for key, val in proj.extensions.items()},
                             self.extension_classes)

        proj.setup()

        self.assertEqual(len(proj.tree.get_pages()), 1)

    def test_subproject(self):
        proj = Project(self)
        sm_path = self._create_sitemap('sitemap.txt', 'index.markdown\n\tsubproject.json')
        index_path = self._create_md_file('index.markdown', '# Project')

        sub_sm_path = self._create_sitemap('subsitemap.txt', 'subindex.markdown')
        sub_index_path = self._create_md_file('subindex.markdown', '# Subproject')
        subconf_path = self._create_conf_file('subproject.json',
                                              {'index': sub_index_path,
                                               'sitemap': sub_sm_path,
                                               'project_name': 'subproject',
                                               'project_version': '0.2'})

        conf = Config({'sitemap': sm_path,
                       'index': index_path,
                       'project_name': 'test-project',
                       'project_version': '0.1',
                       'output': self._output_dir})
        proj.parse_config(conf) 
        proj.setup()

        self.assertEqual(len(proj.tree.get_pages()), 2)
        proj.format(self.link_resolver, self.output)
