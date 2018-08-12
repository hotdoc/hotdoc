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
import os
from hotdoc.tests.fixtures import HotdocTest
from hotdoc.core.exceptions import ConfigError
from hotdoc.core.project import Project, CoreExtension
from hotdoc.core.config import Config
from hotdoc.utils.loggable import Logger


class TestProject(HotdocTest):

    def setUp(self):
        self.dependency_map = {}
        super(TestProject, self).setUp()
        self.extension_classes = {CoreExtension.extension_name: CoreExtension}
        self.private_folder = self.private_folder
        self.output = self._output_dir
        Logger.silent = True
        self.project = None

    def test_basic(self):
        proj = Project(self)
        self.project = proj

        conf = Config({})
        with self.assertRaises(ConfigError):
            proj.parse_name_from_config(conf)
            proj.parse_config(conf)

        sm_path = self._create_sitemap('sitemap.txt', 'index.markdown\n')
        conf = Config({'sitemap': sm_path})
        with self.assertRaises(ConfigError):
            proj.parse_name_from_config(conf)
            proj.parse_config(conf)

        index_path = self._create_md_file('index.markdown', '# Project')
        conf = Config({'sitemap': sm_path,
                       'index': index_path,
                       'project_name': 'test-project',
                       'project_version': '0.1'})
        proj.parse_name_from_config(conf)
        proj.parse_config(conf)

        self.assertDictEqual(
            {key: type(val) for key, val in proj.extensions.items()},
            self.extension_classes)

        proj.setup()

        self.assertEqual(len(proj.tree.get_pages()), 1)

    def test_subproject(self):
        proj = Project(self)
        self.project = proj
        sm_path = self._create_sitemap(
            'sitemap.txt', 'index.markdown\n\tsubproject.json')
        index_path = self._create_md_file('index.markdown', '# Project')

        sub_sm_path = self._create_sitemap(
            'subsitemap.txt', 'subindex.markdown')
        sub_index_path = self._create_md_file(
            'subindex.markdown', '# Subproject')
        self._create_conf_file('subproject.json',
                               {'index': sub_index_path,
                                'sitemap': sub_sm_path,
                                'project_name': 'subproject',
                                'project_version': '0.2'})

        conf = Config({'sitemap': sm_path,
                       'index': index_path,
                       'project_name': 'test-project',
                       'project_version': '0.1',
                       'output': self._output_dir})
        proj.parse_name_from_config(conf)
        proj.parse_config(conf, toplevel=True)
        proj.setup()

        self.assertEqual(len(proj.tree.get_pages()), 2)
        proj.format(self.link_resolver, self.output)

    def test_subproject_extra_assets(self):
        proj = Project(self)
        self.project = proj
        sm_path = self._create_sitemap(
            'sitemap.txt', 'index.markdown\n\tsubproject.json')
        index_path = self._create_md_file('index.markdown', '# Project')

        sub_sm_path = self._create_sitemap(
            'subsitemap.txt', 'subindex.markdown')
        sub_index_path = self._create_md_file(
            'subindex.markdown', '# Subproject')
        sub_asset = self._create_md_file('subassets/fake_asset.md', 'Fakery')
        self._create_conf_file('subproject.json',
                               {'index': sub_index_path,
                                'sitemap': sub_sm_path,
                                'project_name': 'subproject',
                                'extra_assets': [os.path.dirname(sub_asset)],
                                'project_version': '0.2'})

        extra_assets = self._create_md_file(
            'extra_assets/fake_asset.md', 'Main fake')
        conf = Config({'sitemap': sm_path,
                       'index': index_path,
                       'project_name': 'test-project',
                       'project_version': '0.1',
                       'extra_assets': [os.path.dirname(extra_assets)],
                       'output': self._output_dir})
        proj.parse_name_from_config(conf)
        proj.parse_config(conf, toplevel=True)
        proj.setup()

        self.assertEqual(len(proj.tree.get_pages()), 2)
        proj.format(self.link_resolver, self.output)
        proj.write_out(self.output)

        # FIXME: reenable with a different testing strategy
        # pylint: disable=pointless-string-statement
        '''
        sub_output = os.path.join(self._output_dir, 'html', 'subproject-0.2')
        proj_output = os.path.join(
            self._output_dir, 'html', proj.sanitized_name)
        self.assertTrue(os.path.exists(os.path.join(
            sub_output, 'subassets', 'fake_asset.md')))
        self.assertFalse(os.path.exists(os.path.join(
            sub_output, 'extra_assets', 'fake_asset.md')))

        self.assertTrue(os.path.exists(os.path.join(
            proj_output, 'extra_assets', 'fake_asset.md')))
        self.assertFalse(os.path.exists(os.path.join(
            proj_output, 'subassets', 'fake_asset.md')))
        '''

    # FIXME: reenable with a different testing strategy
    # pylint: disable=pointless-string-statement
    '''
    def test_order_subpages_with_subprojects(self):
        proj = Project(self)

        content = 'project.markdown\n\tsubproject1.json\n\tsubproject.json'
        conf_file = self._create_project_config_file(
            'project', sitemap_content=content)
        self._create_project_config_file('subproject')
        self._create_project_config_file('subproject1')

        conf = Config(conf_file=conf_file)

        proj.parse_name_from_config(conf)
        proj.parse_config(conf)
        proj.setup()
        sitemap_json = {}
        pages = proj.tree.get_pages()
        proj.dump_json_sitemap(pages['project.markdown'], sitemap_json, True)
        subpages = sitemap_json['subpages']
        self.assertEqual(len(subpages), 2)

        page0_url = [v for (k, v) in sitemap_json['subpages'][
            0].items() if k == 'url'][0]
        self.assertEqual(page0_url, 'subproject1.html')

        page1_url = [v for (k, v) in sitemap_json['subpages'][
            1].items() if k == 'url'][0]
        self.assertEqual(page1_url, 'subproject.html')
    '''
