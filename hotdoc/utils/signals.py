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

import unittest
import inspect


class Slot:
    """Banana banana"""
    # pylint: disable=too-few-public-methods

    def __init__(self, func, *extra_args):
        self.extra_args = extra_args
        if inspect.ismethod(func):
            self.obj = func.__self__
            self.func = func.__func__
        else:
            self.obj = None
            self.func = func

    def __hash__(self):
        return hash((self.func, self.extra_args))

    def __eq__(self, other):
        return (self.func, self.extra_args, self.obj) == (
            other.func, other.extra_args, other.obj)

    def __ne__(self, other):
        return not self == other

    def __call__(self, *args, **kwargs):
        _args = []
        if self.obj:
            _args.append(self.obj)

        _args += list(args) + list(self.extra_args)
        return self.func(*_args, **kwargs)


class Signal(object):
    """
    The Signalling class
    """

    def __init__(self, optimized=False):
        self._functions = set()
        self._after_functions = set()
        self._optimized = optimized

    def __call__(self, *args, **kargs):
        res_list = []
        # Call handler functions
        for func in self._functions:
            res = func(*args, **kargs)
            if res and self._optimized:
                return res
            res_list.append(res)

        for func in self._after_functions:
            res = func(*args, **kargs)
            if res and self._optimized:
                return res
            res_list.append(res)

        if self._optimized:
            return None

        return res_list

    def connect(self, slot, *extra_args):
        """
        @slot: The method to be called on signal emission

        Connects to @slot
        """
        slot = Slot(slot, *extra_args)
        self._functions.add(slot)

    def connect_after(self, slot, *extra_args):
        """
        @slot: The method to be called at last stage of signal emission

        Connects to the signal after the signals has been handled by other
        connect callbacks.
        """
        slot = Slot(slot, *extra_args)
        self._after_functions.add(slot)

    def disconnect(self, slot, *extra_args):
        """
        Disconnect @slot from the signal
        """
        slot = Slot(slot, *extra_args)
        if slot in self._functions:
            self._functions.remove(slot)
        elif slot in self._after_functions:
            self._after_functions.remove(slot)

    def clear(self):
        """
        Cleanup the signal
        """
        self._functions.clear()
        self._after_functions.clear()


class TestSignals(unittest.TestCase):
    """Banana Banana"""

    def test_connect_func(self):
        """Banana Banana"""
        called = []

        def func(arg, extra_arg):
            """Banana Banana"""
            self.assertEqual(arg, 1)
            self.assertEqual(extra_arg, "extra")
            called.append(True)

        signal = Signal()
        signal.connect(func, "extra")

        signal(1)
        self.assertEqual(called, [True])

    def test_connect_method(self):
        """Banana Banana"""
        called = []
        # pylint: disable=too-few-public-methods

        class _Test(unittest.TestCase):
            """Banana Banana"""

            def method(self, arg, extra_arg):
                """Banana Banana"""
                self.assertEqual(arg, 1)
                self.assertEqual(extra_arg, "extra")
                called.append(True)

        signal = Signal()
        test = _Test()
        signal.connect(test.method, "extra")

        signal(1)
        self.assertEqual(called, [True])
