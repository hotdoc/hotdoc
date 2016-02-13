"""Base Hotdoc Exceptions"""

from hotdoc.utils.loggable import Logger


class HotdocException(Exception):
    """Base Hotdoc exception"""


class ConfigError(HotdocException):
    """Banana banana"""
    pass


class ParsingException(HotdocException):
    """Banana banana"""
    pass


class BadInclusionException(HotdocException):
    """Banana banana"""
    pass


Logger.register_error_code('invalid-config', ConfigError)
Logger.register_error_code('setup-issue', ConfigError)
Logger.register_warning_code('parsing-issue', ParsingException)
