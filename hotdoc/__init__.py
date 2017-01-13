"""The hotdoc main module."""
import cProfile
import os
import sys

# pylint: disable=no-name-in-module
from hotdoc.run_hotdoc import run


def main():
    """The main hotdoc function."""
    run_profile = os.environ.get('HOTDOC_PROFILING', False)
    res = 0

    if run_profile:
        prof = cProfile.Profile()
        res = prof.runcall(run, sys.argv[1:])
        prof.dump_stats('hotdoc-runstats')
    else:
        res = run(sys.argv[1:])

    return res
