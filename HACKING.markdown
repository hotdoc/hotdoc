### Running tests

To run all the tests, at release time for example, simply run `python setup.py test`.

To run a specific test, run `python -m unittest path.to.package.TestCaseClass.test_method`, for example `python -m unittest hotdoc.utils.tests.test_loggable.TestLogger.test_warning`.
