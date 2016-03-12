# -*- coding: utf-8 -*-
# A signal/slot implementation
#
# Author:  Thiago Marcos P. Santos
# Author:  Christopher S. Case
# Author:  David H. Bronke
# Author:  Mathieu Duponchelle
# Author:  Thibault Saunier
# Created: August 28, 2008
# Updated: January 29, 2016
# License: MIT

# http://code.activestate.com/recipes/577980-improved-signalsslots-implementation-in-python/

"""
Simple signalling system
"""

from __future__ import print_function
import inspect
from weakref import WeakSet, WeakKeyDictionary


class Signal(object):
    """
    The Signalling class
    """
    def __init__(self, optimized=False):
        self._functions = WeakSet()
        self._after_functions = WeakSet()
        self._methods = WeakKeyDictionary()
        self._after_methods = WeakKeyDictionary()
        self._optimized = optimized

    def __call__(self, *args, **kargs):
        res_list = []
        # Call handler functions
        for func in self._functions:
            res = func(*args, **kargs)
            if res and self._optimized:
                return res
            res_list.append(res)

        # Call handler methods
        for obj, funcs in self._methods.items():
            for func in funcs:
                res = func(obj, *args, **kargs)
                if res and self._optimized:
                    return res
                res_list.append(res)

        for func in self._after_functions:
            res = func(*args, **kargs)
            if res and self._optimized:
                return res
            res_list.append(res)

        # Call handler methods
        for obj, funcs in self._after_methods.items():
            for func in funcs:
                res = func(obj, *args, **kargs)
                if res and self._optimized:
                    return res
                res_list.append(res)

        if self._optimized:
            return None

        return res_list

    def connect(self, slot):
        """
        @slot: The method to be called on signal emission

        Connects to @slot
        """
        if inspect.ismethod(slot):
            if slot.__self__ not in self._methods:
                self._methods[slot.__self__] = set()

            self._methods[slot.__self__].add(slot.__func__)

        else:
            self._functions.add(slot)

    def connect_after(self, slot):
        """
        @slot: The method to be called at last stage of signal emission

        Connects to the signal after the signals has been handled by other
        connect callbacks.
        """
        if inspect.ismethod(slot):
            if slot.__self__ not in self._after_methods:
                self._after_methods[slot.__self__] = set()

            self._after_methods[slot.__self__].add(slot.__func__)

        else:
            self._after_functions.add(slot)

    def disconnect(self, slot):
        """
        Disconnect @slot from the signal
        """
        if inspect.ismethod(slot):
            if slot.__self__ in self._methods:
                self._methods[slot.__self__].remove(slot.__func__)
            elif slot.__self__ in self._after_methods:
                self._after_methods[slot.__self__].remove(slot.__func__)
        else:
            if slot in self._functions:
                self._functions.remove(slot)
            elif slot in self._after_functions:
                self._after_functions.remove(slot)

    def clear(self):
        """
        Cleanup the signal
        """
        self._functions.clear()
        self._methods.clear()
        self._after_functions.clear()
        self._after_methods.clear()
