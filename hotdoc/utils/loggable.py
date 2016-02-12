"""
Banana banana
"""
import re
import sys
from collections import defaultdict


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
            setattr(self, attrib, self._tigetstr(cap_name) or b'')

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            for i, color in zip(list(range(len(self._COLORS))), self._COLORS):
                setattr(self, color, curses.tparm(set_fg, i) or b'')
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            for i, color in zip(list(range(len(self._ANSICOLORS))),
                                self._ANSICOLORS):
                setattr(self, color, curses.tparm(set_fg_ansi, i) or b'')
        set_bg = self._tigetstr('setb')
        if set_bg:
            for i, color in zip(list(range(len(self._COLORS))), self._COLORS):
                setattr(self, 'BG_' + color, curses.tparm(set_bg, i) or b'')
        set_bg_ansi = self._tigetstr('setab')
        if set_bg_ansi:
            for i, color in zip(list(range(len(self._ANSICOLORS))),
                                self._ANSICOLORS):
                setattr(
                    self, 'BG_' + color, curses.tparm(set_bg_ansi, i) or b'')

    # pylint: disable=no-self-use
    def _tigetstr(self, cap_name):
        import curses
        cap = curses.tigetstr(cap_name) or b''
        return re.sub(r'\$<\d+>[/*]?', '', cap.decode()).encode()


class Loggable(object):

    """Subclasses can inherit from this class to report recoverable errors."""

    _error_type_to_exception = defaultdict()

    _domain_codes = defaultdict(set)

    _warning_type_to_exception = defaultdict()

    log = []
    fatal_warnings = False
    extra_log_data = None

    @staticmethod
    def get_error_codes():
        """Return a list of all possible error codes."""
        return Loggable._error_type_to_exception.keys()

    @staticmethod
    def register_error_code(code, exception_type, domain='default'):
        """Register a new error code"""
        Loggable._error_type_to_exception[code] = (exception_type, domain)
        Loggable._domain_codes[domain].add(code)

    @staticmethod
    def register_warning_code(code, exception_type, domain='default'):
        """Register a new warning code"""
        Loggable._warning_type_to_exception[code] = (exception_type, domain)
        Loggable._domain_codes[domain].add(code)

    @staticmethod
    def error(code, message):
        """Call this to raise an exception and have it stored in the log"""
        raise Loggable._error_type_to_exception[code](message)

    @staticmethod
    def warn(code, message):
        """Call this to either raise an exception or """
        if not Loggable.fatal_warnings:
            domain = Loggable._domain_codes[code]
            Loggable.log.append(
                (Loggable.extra_log_data, domain, code, message))
        else:
            raise Loggable._warning_type_to_exception[code](message)
