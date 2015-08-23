from __future__ import print_function
import inspect
from weakref import WeakSet, WeakKeyDictionary


class Signal(object):
    def __init__(self):
        self._functions = WeakSet()
        self._methods = WeakKeyDictionary()

    def __call__(self, *args, **kargs):
        res = []
        # Call handler functions
        for func in self._functions:
            res.append (func(*args, **kargs))

        # Call handler methods
        for obj, funcs in self._methods.items():
            for func in funcs:
                res.append (func(obj, *args, **kargs))
        return res

    def connect(self, slot):
        if inspect.ismethod(slot):
            if slot.__self__ not in self._methods:
                self._methods[slot.__self__] = set()

            self._methods[slot.__self__].add(slot.__func__)

        else:
            self._functions.add(slot)

    def disconnect(self, slot):
        if inspect.ismethod(slot):
            if slot.__self__ in self._methods:
                self._methods[slot.__self__].remove(slot.__func__)
        else:
            if slot in self._functions:
                self._functions.remove(slot)

    def clear(self):
        self._functions.clear()
        self._methods.clear()
