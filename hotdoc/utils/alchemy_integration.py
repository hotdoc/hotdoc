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
Simple interface with sqlalchemy, implements some useful
data structures.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable

# pylint: disable=invalid-name
Base = declarative_base()


class MutableDict(Mutable, dict):
    """
    A mutable dictionary
    """
    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)
            return Mutable.coerce(key, value)
        else:
            return value

    def __delitem(self, key):
        dict.__delitem__(self, key)
        self.changed()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(self)


class MutableList(Mutable, list):
    """
    A mutable list
    """
    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)
            value = Mutable.coerce(key, value)

        return value

    def __setitem__(self, key, value):
        old_value = list.__getitem__(self, key)
        # pylint: disable=no-member
        for obj, key in self._parents.items():
            # pylint: disable=protected-access
            old_value._parents.pop(obj, None)

        list.__setitem__(self, key, value)
        # pylint: disable=protected-access
        for obj, key in self._parents.items():
            value._parents[obj] = key

        self.changed()

    def append(self, item):
        list.append(self, item)
        self.changed()

    def extend(self, iterable):
        list.extend(self, iterable)
        self.changed()

    def insert(self, index, item):
        list.insert(self, index, item)
        self.changed()

    def remove(self, value):
        list.remove(self, value)
        self.changed()

    def reverse(self):
        list.reverse(self)
        self.changed()

    def pop(self, index=-1):
        item = list.pop(self, index)
        self.changed()
        return item

    def sort(self, cmp_=None, key=None, reverse=False):
        list.sort(self, cmp_, key, reverse)
        self.changed()

    def __getstate__(self):
        for item in self:
            if not isinstance(item, Mutable):
                continue
            # pylint: disable=no-member
            for obj, key in self._parents.items():
                # pylint: disable=protected-access
                item._parents[obj] = key
        return list(self)

    def __setstate__(self, state):
        self[:] = state


class MutableObject(Mutable, object):
    """
    A mutable object
    """
    @classmethod
    def coerce(cls, key, value):
        return value

    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop('_parents', None)
        return d

    def __setstate__(self, state):
        # pylint: disable=attribute-defined-outside-init
        self.__dict__ = state

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        self.changed()
