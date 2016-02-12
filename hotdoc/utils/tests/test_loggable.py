# pylint: disable=missing-docstring
# pylint: disable=invalid-name

import unittest
from hotdoc.utils.loggable import Logger, ERROR, WARNING


class FooError(Exception):
    pass


class BazError(Exception):
    pass


class TestLogger(unittest.TestCase):
    def setUp(self):
        Logger.reset()
        Logger.register_error_code('foo', FooError, 'bar')
        Logger.register_warning_code('baz', BazError, 'bar')

    def test_error(self):
        test_journal = []

        with self.assertRaises(FooError) as cm:
            Logger.error('foo', 'This foo is bad')
        self.assertEqual(cm.exception.message, 'This foo is bad')
        test_journal.append((None, ERROR, 'bar', 'foo', 'This foo is bad'))
        self.assertListEqual(Logger.journal, test_journal)

    def test_warning(self):
        test_journal = []

        Logger.warn('baz', 'This baz is bad')
        test_journal.append((None, WARNING, 'bar', 'baz', 'This baz is bad'))
        self.assertListEqual(Logger.journal, test_journal)

    def test_fatal_warnings(self):
        Logger.fatal_warnings = True
        test_journal = []

        with self.assertRaises(BazError) as cm:
            Logger.warn('baz', 'This baz is bad')
        self.assertEqual(cm.exception.message, 'This baz is bad')
        test_journal.append((None, ERROR, 'bar', 'baz', 'This baz is bad'))
        self.assertListEqual(Logger.journal, test_journal)

    def test_unknown_codes(self):
        with self.assertRaises(AssertionError):
            Logger.warn('does-not-exist', 'Should not exist')
        with self.assertRaises(AssertionError):
            Logger.error('does-not-exist', 'Should not exist')

    def test_ignore_warning(self):
        Logger.add_ignored_code('baz')
        Logger.warn('baz', 'This baz is bad but I do not care')
        self.assertListEqual(Logger.journal, [])

    def test_cannot_ignore_error(self):
        test_journal = []
        Logger.add_ignored_code('foo')
        with self.assertRaises(FooError):
            Logger.error('foo', 'This foo is bad I have to care')
        test_journal.append((None, ERROR, 'bar', 'foo',
                             'This foo is bad I have to care'))
        self.assertListEqual(Logger.journal, test_journal)

    def test_checkpoint(self):
        test_journal = []

        Logger.warn('baz', 'This baz is bad')
        test_journal.append((None, WARNING, 'bar', 'baz', 'This baz is bad'))
        self.assertListEqual(Logger.journal, test_journal)
        self.assertListEqual(Logger.since_checkpoint(), test_journal)
        Logger.checkpoint()
        self.assertListEqual(Logger.since_checkpoint(), [])
        Logger.warn('baz', 'This baz is really bad')
        test_journal.append((None, WARNING, 'bar', 'baz',
                             'This baz is really bad'))
        partial_journal = [(None, WARNING, 'bar', 'baz',
                            'This baz is really bad')]
        self.assertListEqual(Logger.journal, test_journal)
        self.assertListEqual(Logger.since_checkpoint(), partial_journal)

    def test_ignore_domain(self):
        Logger.add_ignored_domain('bar')
        Logger.warn('baz', 'This baz is bad but I do not care')
        self.assertListEqual(Logger.journal, [])
        with self.assertRaises(FooError):
            Logger.error('foo', 'This foo is bad I need to care')


if __name__ == '__main__':
    # Run test suite
    unittest.main()
