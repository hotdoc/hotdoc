# pylint: disable=missing-docstring
# pylint: disable=invalid-name

import unittest
from hotdoc.utils.loggable import Loggable


class FooError(Exception):
    pass


class TestLoggable(unittest.TestCase):
    def setUp(self):
        Loggable.register_error_code('foo', FooError, 'bar')

    def test_basic(self):
        pass

if __name__ == '__main__':
    # Run test suite
    unittest.main()
