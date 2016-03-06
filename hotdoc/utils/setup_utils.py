"""
Banana banana
"""
import os
import sys
import subprocess

from bisect import bisect_left, bisect_right


THEME_VERSION = "0.7"


# pylint: disable=no-self-argument
# pylint: disable=invalid-name
class VersionList(list):
    """
    Banana banana
    """
    def index(a, x):
        'Locate the leftmost value exactly equal to x'
        i = bisect_left(a, x)
        if i != len(a) and a[i] == x:
            return i
        raise ValueError

    def find_lt(a, x):
        'Find rightmost value less than x'
        i = bisect_left(a, x)
        if i:
            return a[i - 1]
        raise ValueError

    def find_le(a, x):
        'Find rightmost value less than or equal to x'
        i = bisect_right(a, x)
        if i:
            return a[i - 1]
        raise ValueError

    def find_gt(a, x):
        'Find leftmost value greater than x'
        i = bisect_right(a, x)
        if i != len(a):
            return a[i]
        raise ValueError

    def find_ge(a, x):
        'Find leftmost item greater than or equal to x'
        i = bisect_left(a, x)
        if i != len(a):
            return a[i]
        raise ValueError


def _check_submodule_status(root, submodules):
    """check submodule status
    Has three return values:
    'missing' - submodules are absent
    'unclean' - submodules have unstaged changes
    'clean' - all submodules are up to date
    """

    if hasattr(sys, "frozen"):
        # frozen via py2exe or similar, don't bother
        return 'clean'

    if not os.path.exists(os.path.join(root, '.git')):
        # not in git, assume clean
        return 'clean'

    for submodule in submodules:
        if not os.path.exists(submodule):
            return 'missing'

    # Popen can't handle unicode cwd on Windows Python 2
    if sys.platform == 'win32' and sys.version_info[0] < 3 \
            and not isinstance(root, bytes):
        root = root.encode(sys.getfilesystemencoding() or 'ascii')
    # check with git submodule status
    proc = subprocess.Popen('git submodule status',
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                            cwd=root)
    status, _ = proc.communicate()
    status = status.decode("ascii", "replace")

    for line in status.splitlines():
        if line.startswith('-'):
            return 'missing'
        elif line.startswith('+'):
            return 'unclean'

    return 'clean'


def _update_submodules(repo_dir):
    """update submodules in a repo"""
    subprocess.check_call("git submodule init", cwd=repo_dir, shell=True)
    subprocess.check_call(
        "git submodule update --recursive", cwd=repo_dir, shell=True)

UNCLEAN_SUBMODULES_MSG =\
    """
    WARNING:

    The submodules are not clean.  This means that either you have
    changed the code in the submodules, or something has gone quite wrong
    with your git repo.  I will continue to try to build, but if
    something goes wrong with the installation, this is probably the
    cause.  You may want to commit any submodule changes you have made.
    """


def require_clean_submodules(repo_root, submodules):
    """Check on git submodules before distutils can do anything
    Since distutils cannot be trusted to update the tree
    after everything has been set in motion,
    this is not a distutils command.
    """
    # PACKAGERS: Add a return here to skip checks for git submodules

    # don't do anything if nothing is actually supposed to happen
    for do_nothing in (
            '-h', '--help', '--help-commands', 'clean', 'submodule'):
        if do_nothing in sys.argv:
            return

    status = _check_submodule_status(repo_root, submodules)

    if status == "missing":
        print "checking out submodules for the first time"
        _update_submodules(repo_root)
    elif status == "unclean":
        print UNCLEAN_SUBMODULES_MSG
