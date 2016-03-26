To build or rebuild re2c scanners, run make in this directory.

To build the C extensions, run python setup.py develop in the top-level directory, as soon as a C source changes it will rebuild everything (including cmark) because setuptools is clever like that. If this becomes too much of a hassle we'll complexify the build a bit to compile cmark separately, but it's bearable enough that I won't go through the hoops just yet.
