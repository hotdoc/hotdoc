from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable

Base = declarative_base()

class MutableDict(Mutable, dict):
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
    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)
            value = Mutable.coerce(key, value)

        return value

    def __setitem__(self, key, value):
        old_value = list.__getitem__(self, key)
        for obj, key in self._parents.items():
            old_value._parents.pop(obj, None)

        list.__setitem__(self, key, value)
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

    def sort(self, cmp=None, key=None, reverse=False):
        list.sort(self, cmp, key, reverse)
        self.changed()

    def __getstate__(self):
        for item in self:
            if not isinstance (item, Mutable):
                continue
            for obj, key in self._parents.items():
                item._parents[obj] = key
        return list(self)

    def __setstate__(self, state):
        self[:] = state


class MutableObject(Mutable, object):
    @classmethod
    def coerce(cls, key, value):
        return value

    def __getstate__(self): 
        d = self.__dict__.copy()
        d.pop('_parents', None)
        return d

    def __setstate__(self, state):
        self.__dict__ = state

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        self.changed()
