### Setting up environment for contributing

Install required tools and git hooks:
```
pip install -r dev-requirements.txt
pre-commit install --install-hooks
```

### Running tests

To run all the tests, at release time for example, simply run `python3 -m pytest`.

To run a specific test, run `python -m unittest path.to.package.TestCaseClass.test_method`, for example `python -m unittest hotdoc.utils.tests.test_loggable.TestLogger.test_warning`.

### Profiling hotdoc

To profile a hotdoc run, simply set the HOTDOC_PROFILING environment variable to 1, like so:

```
HOTDOC_PROFILING=1 hotdoc run
```

A file named `hotdoc-runstats` will be created in the current directory, a handy tool to examine it is `gprof2dot.py`, install it with:

```
pip install gprof2dot
```

Then run:

```
gprof2dot -f pstats hotdoc-runstats | dot -Tsvg -o profile.svg
```

You can then inspect the call tree profile with your preferred image viewer:

```
xdg-open profile.svg
```

### Updating cmark

```
git submodule update --remote
```
