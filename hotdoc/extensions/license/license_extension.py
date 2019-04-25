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

import os

from collections import namedtuple

from schema import Schema, SchemaError, And, Use, Optional

from hotdoc.core.extension import Extension
from hotdoc.core.formatter import Formatter
from hotdoc.core.tree import Page
from hotdoc.core.exceptions import HotdocException
from hotdoc.utils.loggable import error, Logger


class NoSuchLicenseException(HotdocException):
    """
    Raised when an unknown license is used
    """
    pass


Logger.register_error_code('no-such-license', NoSuchLicenseException,
                           domain='license-extension')


DESCRIPTION =\
    """
This extension helps licensing your hotdoc project
"""


HERE = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(HERE, 'data')


BASE_COPYRIGHT_SCHEMA = {'name': And(str, len),
                         Optional('email'): And(str, len),
                         Optional('years', default=[]): Schema([Use(int)])}

AUTHOR_SCHEMA = BASE_COPYRIGHT_SCHEMA.copy()
AUTHOR_SCHEMA[Optional('has-copyright')] = And(bool)

Page.meta_schema[Optional('extra-copyrights')] =\
    Schema([BASE_COPYRIGHT_SCHEMA])

Page.meta_schema[Optional('authors')] =\
    Schema([AUTHOR_SCHEMA])

Page.meta_schema[Optional('license')] =\
    Schema(And(str, len))
Page.meta_schema[Optional('code-samples-license')] =\
    Schema(And(str, len))


class License(object):

    def __init__(self, short_name, full_name, url):
        self.short_name = short_name
        self.full_name = full_name
        self.url = url

    @property
    def logo_path(self):
        path = os.path.join(DATA_DIR, '%s.png' % self.short_name)
        if os.path.exists(path):
            return path
        return None

    @property
    def plain_text_path(self):
        path = os.path.join(DATA_DIR, '%s.txt' % self.short_name)
        assert os.path.exists(path)
        return path


CopyrightHolder = namedtuple('CopyrightHolder',
                             ['name', 'email', 'years', 'has_copyright'])


CCBYSA_4_0_LICENSE = License("CC-BY-SAv4.0",
                             "Creative Commons Attribution-ShareAlike "
                             "4.0 International",
                             "https://creativecommons.org/licenses/by-sa/4.0/")

CC0_LICENSE = License("CC0-1.0",
                      "Creative Commons Zero 1.0 Universal.",
                      "http://spdx.org/licenses/CC0-1.0")

ALL_LICENSES = {
    "CC-BY-SAv4.0": CCBYSA_4_0_LICENSE,
    "CC-BY-SA": CCBYSA_4_0_LICENSE,
    "CC0-1.0": CC0_LICENSE,
}


class LicenseExtension(Extension):
    extension_name = 'license-extension'
    argument_prefix = 'license'
    connected = False
    installed_assets = set()

    def __init__(self, app, project):
        Extension.__init__(self, app, project)
        self.default_license = None
        self.default_code_samples_license = None
        self.default_copyright_holders = []
        self.authors_hold_copyright = True

    def __license_for_page(self, page, code_samples=False):
        if code_samples:
            key = 'code-samples-license'
        else:
            key = 'license'
        if key in page.meta:
            short_name = page.meta[key]
            try:
                license_ = ALL_LICENSES[short_name]
            except KeyError:
                error('no-such-license',
                      'In %s: no such license %s' % (page.source_file,
                                                     short_name))
        else:
            if code_samples:
                license_ = self.default_code_samples_license
            else:
                license_ = self.default_license

        return license_

    def __authors_for_page(self, page):
        authors = []
        for data in page.meta.get('authors') or []:
            authors.append(
                CopyrightHolder(data.get('name'),
                                data.get('email'),
                                [str(year) for year in data.get('years')],
                                data.get('has-copyright',
                                         self.authors_hold_copyright)))
        return authors

    def __extra_copyrights_for_page(self, page):
        extra_copyrights = []
        for data in page.meta.get('extra-copyrights') or []:
            extra_copyrights.append(
                CopyrightHolder(data.get('name'),
                                data.get('email'),
                                [str(year) for year in data.get('years')],
                                True))

        return extra_copyrights or self.default_copyright_holders

    def __copyrights_for_page(self, page):
        return (self.__authors_for_page(page) +
                self.__extra_copyrights_for_page(page))

    def license_content(self, page, license_, designation):
        template = Formatter.engine.get_template('license.html')
        if license_.logo_path:
            logo_path = os.path.join(
                'assets', os.path.basename(license_.logo_path))
        else:
            logo_path = None

        formatted = template.render(
            {'license': license_,
             'logo_path': logo_path,
             'content_designation': designation})
        page.output_attrs['html']['extra_footer_html'].insert(0, formatted)

        LicenseExtension.installed_assets.add(license_.plain_text_path)
        if license_.logo_path:
            LicenseExtension.installed_assets.add(license_.logo_path)

    def __formatting_page_cb(self, formatter, page):
        # hotdoc doesn't claim a copyright
        if page.generated:
            return

        copyrights = self.__copyrights_for_page(page)
        if copyrights:
            template = Formatter.engine.get_template('copyrights.html')
            formatted = template.render({'copyrights': copyrights})
            page.output_attrs['html']['extra_footer_html'].insert(0, formatted)

        license_ = self.__license_for_page(page)
        code_license = self.__license_for_page(page, code_samples=True)

        if license_ and (license_ == code_license or not code_license):
            self.license_content(page, license_, 'All content in this page is')
        else:
            if code_license:
                self.license_content(page, code_license,
                                     'Code snippets in this page are')
            if license_:
                self.license_content(page, license_,
                                     'Documentation in this page is')

    def __get_extra_files_cb(self, formatter):
        res = []
        for asset in LicenseExtension.installed_assets:
            src = asset
            dest = os.path.basename(src)
            res.append((src, dest))
        return res

    def setup(self):
        super(LicenseExtension, self).setup()
        for ext in self.project.extensions.values():
            ext.formatter.formatting_page_signal.connect(
                self.__formatting_page_cb)

        if not LicenseExtension.connected:
            Formatter.get_extra_files_signal.connect(
                self.__get_extra_files_cb)
            LicenseExtension.connected = True

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('License extension',
                                          DESCRIPTION)
        group.add_argument("--default-license",
                           help="Default license",
                           dest="default_license",
                           action='store',
                           default=None)
        group.add_argument("--default-code-samples-license",
                           help="Default license for code samples",
                           dest="default_code_samples_license",
                           action='store',
                           default=None)
        group.add_argument("--authors-hold-copyright",
                           help="Whether authors hold a copyright by default."
                           "This can be overriden on a per-page basis",
                           dest="authors_hold_copyright", action='store')

    def parse_toplevel_config(self, config):
        super().parse_toplevel_config(config)
        template_path = os.path.join(HERE, 'html_templates')
        Formatter.engine.loader.searchpath.append(template_path)

    def parse_config(self, config):
        super(LicenseExtension, self).parse_config(config)
        short_name = config.get("default_license")
        if short_name is not None:
            try:
                self.default_license = ALL_LICENSES[short_name]
            except KeyError:
                error('no-such-license', 'Unknown license : %s' % short_name)

        short_name = config.get("default_code_samples_license")
        if short_name is not None:
            try:
                self.default_code_samples_license = ALL_LICENSES[short_name]
            except KeyError:
                error('no-such-license', 'Unknown license : %s' % short_name)

        data = config.get("default_copyright_holders")
        if data:
            try:
                data = Schema([BASE_COPYRIGHT_SCHEMA]).validate(data)
            except SchemaError:
                error('invalid-config',
                      'Invalid default copyright holders metadata : %s' %
                      str(data))
            for datum in data:
                self.default_copyright_holders.append(
                    CopyrightHolder(datum.get('name'),
                                    datum.get('email'),
                                    [str(year) for year in datum.get('years')],
                                    True))
        self.authors_hold_copyright = config.get(
            "authors_hold_copyright", True)


def get_extension_classes():
    return [LicenseExtension]
