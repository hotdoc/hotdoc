# -*- coding: utf-8 -*-
#
# Copyright © 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""
Banana banana
"""

import os
import re
import sys
import io
from collections import defaultdict, namedtuple

from hotdoc.utils.configurable import Configurable
from hotdoc.core.exceptions import ConfigError, ParsingException


# pylint: disable=too-few-public-methods
class TerminalController(object):
    """
    Banana banana
    """
    # Cursor movement:
    BOL = ''             # : Move the cursor to the beginning of the line
    # pylint: disable=invalid-name
    UP = ''              # : Move the cursor up one line
    DOWN = ''            # : Move the cursor down one line
    LEFT = ''            # : Move the cursor left one char
    RIGHT = ''           # : Move the cursor right one char

    # Deletion:
    CLEAR_SCREEN = ''    # : Clear the screen and move to home position
    CLEAR_EOL = ''       # : Clear to the end of the line.
    CLEAR_BOL = ''       # : Clear to the beginning of the line.
    CLEAR_EOS = ''       # : Clear to the end of the screen

    # Output modes:
    BOLD = ''            # : Turn on bold mode
    BLINK = ''           # : Turn on blink mode
    DIM = ''             # : Turn on half-bright mode
    REVERSE = ''         # : Turn on reverse-video mode
    NORMAL = ''          # : Turn off all modes

    # Cursor display:
    HIDE_CURSOR = ''     # : Make the cursor invisible
    SHOW_CURSOR = ''     # : Make the cursor visible

    # Terminal size:
    COLS = None          # : Width of the terminal (None for unknown)
    LINES = None         # : Height of the terminal (None for unknown)

    # Foreground colors:
    BLACK = BLUE = GREEN = CYAN = RED = MAGENTA = YELLOW = WHITE = ''

    # Background colors:
    BG_BLACK = BG_BLUE = BG_GREEN = BG_CYAN = ''
    BG_RED = BG_MAGENTA = BG_YELLOW = BG_WHITE = ''

    _STRING_CAPABILITIES = """
    BOL=cr UP=cuu1 DOWN=cud1 LEFT=cub1 RIGHT=cuf1
    CLEAR_SCREEN=clear CLEAR_EOL=el CLEAR_BOL=el1 CLEAR_EOS=ed BOLD=bold
    BLINK=blink DIM=dim REVERSE=rev UNDERLINE=smul NORMAL=sgr0
    HIDE_CURSOR=cinvis SHOW_CURSOR=cnorm""".split()
    _COLORS = """BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE""".split()
    _ANSICOLORS = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".split()

    def __init__(self, term_stream=sys.stdout):
        # Curses isn't available on all platforms
        try:
            import curses
        except ImportError:
            return

        # If the stream isn't a tty, then assume it has no capabilities.
        if not term_stream.isatty():
            return

        # Check the terminal type.  If we fail, then assume that the
        # terminal has no capabilities.
        try:
            curses.setupterm()
        # pylint: disable=bare-except
        except:
            return

        # Look up numeric capabilities.
        TerminalController.COLS = curses.tigetnum('cols')
        TerminalController.LINES = curses.tigetnum('lines')

        # Look up string capabilities.
        for capability in self._STRING_CAPABILITIES:
            (attrib, cap_name) = capability.split('=')
            setattr(self, attrib, self._tigetstr(cap_name).decode() or '')

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            for i, color in zip(list(range(len(self._COLORS))), self._COLORS):
                setattr(self, color, curses.tparm(set_fg, i).decode() or '')
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            for i, color in zip(list(range(len(self._ANSICOLORS))),
                                self._ANSICOLORS):
                setattr(self,
                        color, curses.tparm(set_fg_ansi, i).decode() or '')
        set_bg = self._tigetstr('setb')
        if set_bg:
            for i, color in zip(list(range(len(self._COLORS))), self._COLORS):
                setattr(self,
                        'BG_' + color, curses.tparm(set_bg, i).decode() or '')
        set_bg_ansi = self._tigetstr('setab')
        if set_bg_ansi:
            for i, color in zip(list(range(len(self._ANSICOLORS))),
                                self._ANSICOLORS):
                setattr(
                    self,
                    'BG_' + color, curses.tparm(set_bg_ansi, i).decode() or '')

    # pylint: disable=no-self-use
    def _tigetstr(self, cap_name):
        import curses
        cap = curses.tigetstr(cap_name) or b''
        return re.sub(r'\$<\d+>[/*]?', '', cap.decode()).encode()

TERMC = TerminalController()

(DEBUG,
 INFO,
 WARNING,
 ERROR) = list(range(4))


LogEntry = namedtuple('LogEntry', ['level', 'domain', 'code', 'message'])


def _force_print(out, msg):
    try:
        out.write(msg)
    except UnicodeEncodeError:
        iostr = io.StringIO()
        iostr.write(msg)
        cleaned = iostr.getvalue().encode('ascii', 'replace').decode('ascii')
        out.write(cleaned)


def _print_entry(entry):
    out = sys.stdout
    if entry.level > INFO:
        out = sys.stderr

    if entry.level == DEBUG:
        _force_print(out, TERMC.CYAN + 'DEBUG' + TERMC.NORMAL)
    elif entry.level == INFO:
        _force_print(out, TERMC.GREEN + 'INFO' + TERMC.NORMAL)
    elif entry.level == WARNING:
        _force_print(out, TERMC.YELLOW + 'WARNING' + TERMC.NORMAL)
    elif entry.level == ERROR:
        _force_print(out, TERMC.RED + 'ERROR' + TERMC.NORMAL)

    _force_print(out, ': [%s]:' % entry.domain)

    if entry.code:
        _force_print(out, ' (%s):' % entry.code)

    _force_print(out, ' %s\n' % entry.message)
    out.flush()


class Logger(Configurable):

    """Subclasses can inherit from this class to report recoverable errors."""

    _error_code_to_exception = defaultdict()
    _domain_codes = defaultdict(set)
    _warning_code_to_exception = defaultdict()
    journal = []
    fatal_warnings = False
    raise_on_fatal_warnings = False
    _ignored_codes = set()
    _ignored_domains = set()
    _last_checkpoint = 0
    _verbosity = WARNING
    silent = False
    n_fatal_warnings = 0

    @staticmethod
    def register_error_code(code, exception_type, domain='core'):
        """Register a new error code"""
        Logger._error_code_to_exception[code] = (exception_type, domain)
        Logger._domain_codes[domain].add(code)

    @staticmethod
    def register_warning_code(code, exception_type, domain='core'):
        """Register a new warning code"""
        Logger._warning_code_to_exception[code] = (exception_type, domain)
        Logger._domain_codes[domain].add(code)

    @staticmethod
    def _log(code, message, level, domain):
        """Call this to add an entry in the journal"""
        entry = LogEntry(level, domain, code, message)
        Logger.journal.append(entry)

        if Logger.silent:
            return

        if level >= Logger._verbosity:
            _print_entry(entry)

    @staticmethod
    def error(code, message, **kwargs):
        """Call this to raise an exception and have it stored in the journal"""
        assert code in Logger._error_code_to_exception
        exc_type, domain = Logger._error_code_to_exception[code]
        exc = exc_type(message, **kwargs)
        Logger._log(code, exc.message, ERROR, domain)
        raise exc

    @staticmethod
    def warn(code, message, **kwargs):
        """
        Call this to store a warning in the journal.

        Will raise if `Logger.fatal_warnings` is set to True and
        `Logger.raise_on_fatal_warnings` as well.
        """

        if code in Logger._ignored_codes:
            return

        assert code in Logger._warning_code_to_exception
        exc_type, domain = Logger._warning_code_to_exception[code]

        if domain in Logger._ignored_domains:
            return

        level = WARNING
        if Logger.fatal_warnings:
            level = ERROR

        exc = exc_type(message, **kwargs)

        Logger._log(code, exc.message, level, domain)

        if Logger.fatal_warnings:
            if Logger.raise_on_fatal_warnings:
                raise exc
            else:
                Logger.n_fatal_warnings += 1

    @staticmethod
    def debug(message, domain):
        """Log debugging information"""
        if domain in Logger._ignored_domains:
            return

        Logger._log(None, message, DEBUG, domain)

    @staticmethod
    def info(message, domain):
        """Log simple info"""
        if domain in Logger._ignored_domains:
            return

        Logger._log(None, message, INFO, domain)

    @staticmethod
    def add_ignored_code(code):
        """Add a code to ignore. Errors cannot be ignored."""
        Logger._ignored_codes.add(code)

    @staticmethod
    def add_ignored_domain(code):
        """Add a domain to ignore. Errors cannot be ignored."""
        Logger._ignored_domains.add(code)

    @staticmethod
    def checkpoint():
        """Add a checkpoint"""
        Logger._last_checkpoint = len(Logger.journal)

    @staticmethod
    def since_checkpoint():
        """Get journal since last checkpoint"""
        return Logger.journal[Logger._last_checkpoint:]

    @staticmethod
    def get_issues():
        """Get actual issues in the journal."""
        issues = []
        for entry in Logger.journal:
            if entry.level >= WARNING:
                issues.append(entry)
        return issues

    @staticmethod
    def reset():
        """Resets Logger to its initial state"""
        Logger.journal = []
        Logger.fatal_warnings = False
        Logger.raise_on_fatal_warnings = False
        Logger._ignored_codes = set()
        Logger._ignored_domains = set()
        Logger._verbosity = 2
        Logger._last_checkpoint = 0
        Logger.n_fatal_warnings = 0

    @staticmethod
    def add_arguments(parser):
        """Banana banana
        """
        group = parser.add_argument_group(
            'Logger', 'logging options')
        group.add_argument("--verbose", '-v', action="count",
                           dest="verbose",
                           help="Turn on verbosity, -vv for debug")
        group.add_argument("--fatal-warnings", action="store_true",
                           dest="fatal_warnings", help="Make warnings fatal")

    @staticmethod
    def set_verbosity(verbosity):
        """Banana banana
        """
        Logger._verbosity = min(max(0, WARNING - verbosity), 2)
        debug("Verbosity set to %d" % (WARNING - Logger._verbosity), 'logging')

    @staticmethod
    def parse_config(config):
        Logger._verbosity = max(0, Logger._verbosity - (
            config.get('verbose') or 0))

        Logger.fatal_warnings = bool(config.get("fatal_warnings"))


def info(message, domain='core'):
    """Shortcut to `Logger.info`"""
    Logger.info(message, domain)


def warn(code, message, **kwargs):
    """Shortcut to `Logger.warn`"""
    Logger.warn(code, message, **kwargs)


def debug(message, domain='core'):
    """Shortcut to `Logger.debug`"""
    Logger.debug(message, domain)


def error(code, message, **kwargs):
    """Shortcut to `Logger.error`"""
    Logger.error(code, message, **kwargs)


ENV_VERBOSITY = os.getenv('HOTDOC_DEBUG')
if ENV_VERBOSITY is not None:
    Logger.set_verbosity(int(ENV_VERBOSITY))

Logger.register_error_code('invalid-config', ConfigError)
Logger.register_error_code('setup-issue', ConfigError)
Logger.register_warning_code('parsing-issue', ParsingException)
