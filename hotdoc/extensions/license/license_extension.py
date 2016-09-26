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

import os
import argparse

from schema import Schema, SchemaError, And, Use, Optional

from hotdoc.core.base_extension import BaseExtension
from hotdoc.core.base_formatter import Formatter
from hotdoc.core.doc_tree import Page
from hotdoc.core.exceptions import HotdocException
from hotdoc.utils.loggable import error, warn, Logger


class NoSuchLicenseException(HotdocException):
    """
    Raised when an unknown license is used
    """
    pass


Logger.register_error_code('no-such-license', NoSuchLicenseException,
                           domain='license-extension')


DESCRIPTION=\
"""
This extension helps licensing your hotdoc project
"""


HERE = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(HERE, 'data')


base_copyright_schema = {'name': And(unicode, len),
                         Optional('email'): And(unicode, len),
                         Optional('years'): Schema([Use(int)])}

author_schema = base_copyright_schema.copy()
author_schema[Optional('has-copyright')] = And(bool)

Page.meta_schema[Optional('extra-copyrights')] =\
        Schema([base_copyright_schema])

Page.meta_schema[Optional('authors')] =\
        Schema([author_schema])

Page.meta_schema[Optional('license')] =\
        Schema(And(unicode, len))


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
        assert(os.path.exists(path))
        return path


class CopyrightHolder(object):
    def __init__(self, name, email, years):
        self.name = name
        self.email = email
        self.years = [str(year) for year in years or []]
        self.has_copyright = True


class Author(CopyrightHolder):
    def __init__(self, name, email, years, has_copyright):
        CopyrightHolder.__init__(self, name, email, years)
        self.has_copyright = has_copyright


CCBYSA_4_0_LICENSE = License("CC-BY-SAv4.0",
                         "Creative Commons Attribution-ShareAlike 4.0 International",
                         "https://creativecommons.org/licenses/by-sa/4.0/")


ALL_LICENSES = {
        "CC-BY-SAv4.0": CCBYSA_4_0_LICENSE,
        "CC-BY-SA": CCBYSA_4_0_LICENSE,
}

def _copyright_holder_from_data(data):
    return CopyrightHolder(data.get('name'),
                           data.get('email'),
                           data.get('years'))

class LicenseExtension(BaseExtension):
    extension_name = 'license-extension'
    argument_prefix = 'license'
    default_license = None
    default_copyright_holders = []
    authors_hold_copyright = True

    def __init__(self, doc_repo):
        BaseExtension.__init__(self, doc_repo)
        self.__installed_assets = set()

    def __license_for_page(self, page):
        if 'license' in page.meta:
            short_name = page.meta['license']
            try:
                license = ALL_LICENSES[short_name]
            except KeyError:
                error('no-such-license',
                      'In %s: no such license %s' % (page.source_file,
                                                     short_name))
        else:
            license = LicenseExtension.default_license

        return license

    def __authors_for_page(self, page):
        authors = []
        for data in page.meta.get('authors') or []:
            authors.append(Author(data.get('name'),
                                  data.get('email'),
                                  data.get('years'),
                                  data.get('has-copyright',
                                      LicenseExtension.authors_hold_copyright)))
        return authors

    def __extra_copyrights_for_page(self, page):
        extra_copyrights = []
        for data in page.meta.get('extra-copyrights') or []:
            extra_copyrights.append(_copyright_holder_from_data(data))

        return extra_copyrights or LicenseExtension.default_copyright_holders

    def __copyrights_for_page(self, page):
        return self.__authors_for_page(page) + self.__extra_copyrights_for_page(page)

    def __formatting_page_cb(self, formatter, page):
        # hotdoc doesn't claim a copyright
        if page.generated:
            return

        copyrights = self.__copyrights_for_page(page)
        if copyrights:
            template = formatter.engine.get_template('copyrights.html')
            formatted = template.render({'copyrights': copyrights})
            page.output_attrs['html']['extra_footer_html'].insert(0, formatted)

        license = self.__license_for_page(page)
        if license:
            template = formatter.engine.get_template('license.html')
            if license.logo_path:
                logo_path = os.path.join('assets', os.path.basename(license.logo_path))
            else:
                logo_path = None

            formatted = template.render({'license': license, 'logo_path': logo_path})
            page.output_attrs['html']['extra_footer_html'].insert(0, formatted)

            self.__installed_assets.add(license.plain_text_path)
            if license.logo_path:
                self.__installed_assets.add(license.logo_path)

    def __get_extra_files_cb(self, formatter):
        res = []
        for asset in self.__installed_assets:
            src = asset
            dest = os.path.basename(src)
            res.append((src, dest))
        return res

    def setup(self):
        Formatter.formatting_page_signal.connect(self.__formatting_page_cb)
        Formatter.get_extra_files_signal.connect(self.__get_extra_files_cb)

        for ext in self.doc_repo.extensions.values():
            formatter = ext.formatters.get('html')
            template_path = os.path.join(HERE, 'html_templates')
            formatter.engine.loader.searchpath.append(template_path)

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('License extension',
                DESCRIPTION)
        group.add_argument("--default-license",
            help="Default license",
            dest="default_license", action='store', default=None)
        group.add_argument("--authors-hold-copyright",
            help="Whether authors hold a copyright by default."
                 "This can be overriden on a per-page basis",
            dest="authors_hold_copyright", action='store')

    @staticmethod
    def parse_config(doc_repo, config):
        short_name = config.get("default-license")
        if short_name is not None:
            try:
                LicenseExtension.default_license = ALL_LICENSES[short_name]
            except KeyError:
                error('no-such-license', 'Unknown license : %s' % short_name)
        data = config.get("default-copyright-holders")
        if data:
            try:
                data = Schema([base_copyright_schema]).validate(data)
            except SchemaError:
                error('invalid-config',
                        'Invalid default copyright holders metadata : %s' % str(data))
            for _ in data:
                LicenseExtension.default_copyright_holders.append(
                    _copyright_holder_from_data(_))
        LicenseExtension.authors_hold_copyright = config.get(
            "authors_hold_copyright", True)


def get_extension_classes():
    return [LicenseExtension]
