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
Banana banana
"""
import urllib.parse
from hotdoc.utils.loggable import Logger, warn
from hotdoc.core.exceptions import MissingLinkException
Logger.register_warning_code('mandatory-link-not-found', MissingLinkException,
                             domain='links')

from hotdoc.utils.signals import Signal


def dict_to_html_attrs(dict_):
    """
    Banana banana
    """
    res = ' '.join('%s="%s"' % (k, v) for k, v in dict_.items())
    return res


class Link:
    """
    Banana banana
    """
    resolving_title_signal = Signal()

    def __init__(self, ref, title, id_, mandatory=False):
        self.ref = None
        self._title = None
        # Whether the link should be always resolved when true and a warning
        # otherwise
        self.__mandatory = mandatory
        # Ensure we warn only once for a unresolved mandatory link
        self.__warned = False

        if title:
            self._title = str(title)
        if ref:
            self.ref = str(ref)

        self.id_ = id_

    @property
    def title(self):
        """
        Banana banana
        """
        resolved_title = Link.resolving_title_signal(self)
        resolved_title = [elem for elem in resolved_title if elem is not
                          None]
        if resolved_title:
            return str(resolved_title[0])
        return self._title

    @title.setter
    def title(self, value):
        self._title = str(value)

    def get_title(self):
        """
        Convenience wrapper for the `title` property.

        Exists mainly to facilitate the task of the cmark C extension.
        """
        return self.title

    def get_link(self, link_resolver):
        """
        Banana banana
        """
        res = link_resolver.resolving_link_signal(self)

        if not res:
            ref = self.ref
        else:
            ref = res[0] or self.ref

        if self.__mandatory and not self.__warned:
            if not ref:
                warn('mandatory-link-not-found',
                     'Mandatory link %s could not be resolved' % self)
            self.__warned = True

        if not res:
            return ref, None

        if res[1]:
            return ref, dict_to_html_attrs(res[1])
        return ref, None

    def __repr__(self):
        return "Link %s -> %s (%s)" % (self.id_, self.ref, self._title)


class LinkResolver:
    """
    Banana banana
    """

    def __init__(self, database):
        self.__links = {}
        self.__doc_db = database
        self.get_link_signal = Signal()
        self.resolving_link_signal = Signal(optimized=True)

    # pylint: disable=too-many-return-statements
    def get_named_link(self, name):
        """
        Banana banana
        """
        return self.__get_named_link(name)

    def __get_named_link(self, name, recursed=False):
        url_components = urllib.parse.urlparse(name)
        if bool(url_components.netloc):
            return Link(name, None, name)

        if name in self.__links:
            return self.__links[name]

        sym = self.__doc_db.get_symbol(name)
        if sym and sym.link:
            self.__links[name] = sym.link
            return sym.link

        lazy_loaded = self.get_link_signal(self, name)
        lazy_loaded = [elem for elem in lazy_loaded if elem is not None]
        if lazy_loaded:
            link = lazy_loaded[0]
            self.__links[name] = link
            link.id_ = name
            return link

        if url_components.scheme in ['man', 'mailto']:
            return Link(name, None, name)

        # Formatters should warn later about broken anchor links
        if bool(url_components.fragment) and not bool(url_components.path):
            return Link(name, None, name)

        if name.endswith('s') and not recursed:
            return self.__get_named_link(name[:-1], True)

        return None

    def add_link(self, link):
        """
        Banana banana
        """
        if link.id_ not in self.__links:
            self.__links[link.id_] = link

    def upsert_link(self, link, overwrite_ref=False):
        """
        Banana banana
        """
        elink = self.__links.get(link.id_)

        if elink:
            if elink.ref is None or overwrite_ref and link.ref:
                elink.ref = link.ref
            # pylint: disable=protected-access
            if link._title is not None:
                # pylint: disable=protected-access
                elink.title = link._title
            return elink

        if not overwrite_ref:
            sym = self.__doc_db.get_symbol(link.id_)
            if sym and sym.link:
                self.__links[link.id_] = sym.link
                return sym.link

        self.add_link(link)
        return link
