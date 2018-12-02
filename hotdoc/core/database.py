# -*- coding: utf-8 -*-
#
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

"""Banana banana
"""
import os
import pickle

# pylint: disable=import-error
# pylint: disable=import-error
from hotdoc.core.exceptions import HotdocException
from hotdoc.core.symbols import Symbol
from hotdoc.utils.signals import Signal
from hotdoc.utils.loggable import debug, warn, Logger


class RedefinedSymbolException(HotdocException):
    '''
    Exception raised when a symbol is defined twice in the same run
    '''
    pass


Logger.register_warning_code(
    'symbol-redefined', RedefinedSymbolException, 'extension')

# pylint: disable=too-few-public-methods


class ProxySymbol(Symbol):
    """A proxy type to handle aliased symbols"""
    __tablename__ = 'proxy_symbols'

    def __init__(self, **kwargs):
        self.target = None
        Symbol.__init__(self, **kwargs)


# pylint: disable=too-many-instance-attributes
class Database:
    """
    A store of comments and symbols. Eventually, during the documentation
    generation phase, comments and symbols are matched up (using
    `hotdoc.core.comment.Comment.name` and
    `hotdoc.core.symbol.Symbol.unique_name`) to determine what goes into the
    generated documentation and how it is described.
    """

    def __init__(self, private_folder):
        self.comment_added_signal = Signal()

        self.__comments = {}
        self.__symbols = {}
        self.__aliases = {}
        self.__symbol_folder = os.path.join(private_folder or '/tmp',
                                            "symbols")
        self.__aliases_folder = os.path.join(private_folder or '/tmp',
                                             "aliases")
        self.__comments_folder = os.path.join(private_folder or '/tmp',
                                              "comments")

    def add_comment(self, comment):
        """
        Add a comment to the database.

        Args:
            comment (hotdoc.core.Comment): comment to add
        """
        if not comment:
            return

        self.__comments[comment.name] = comment
        self.comment_added_signal(self, comment)

    def get_comment(self, name):
        """
        Banana banana
        """
        comment = self.__comments.get(name)

        if comment:
            return comment

        aliases = self.__get_aliases(name)
        for alias in aliases:
            comment = self.__comments.get(alias)
            if comment:
                return comment

        return None

    def create_symbol(self, type_, **kwargs):
        """
        Banana banana
        """
        unique_name = kwargs.get('unique_name')
        if not unique_name:
            unique_name = kwargs.get('display_name')
            kwargs['unique_name'] = unique_name

        filename = kwargs.get('filename')
        if filename:
            filename = os.path.abspath(filename)
            kwargs['filename'] = os.path.abspath(filename)

        if unique_name in self.__symbols:
            warn('symbol-redefined', "%s(unique_name=%s, filename=%s, project=%s)"
                 " has already been defined: %s" % (type_.__name__, unique_name, filename,
                                                    kwargs.get('project_name'),
                                                    self.get_symbol(unique_name)))
            return None

        aliases = kwargs.pop('aliases', [])
        for alias in aliases:
            self.create_symbol(ProxySymbol,
                               unique_name=alias,
                               target=unique_name)

        symbol = type_()
        debug('Created symbol with unique name %s' % unique_name,
              'symbols')

        for key, value in list(kwargs.items()):
            setattr(symbol, key, value)

        self.__symbols[unique_name] = symbol
        for alias in aliases:
            self.__symbols[alias] = symbol
        self.__aliases[unique_name] = aliases

        return symbol

    @staticmethod
    def __get_pickle_path(folder, name, create_if_required=False):
        fname = os.path.join(folder, name.lstrip('/'))
        if create_if_required:
            os.makedirs(os.path.dirname(fname), exist_ok=True)
        return fname

    def persist(self):
        """
        Banana banana
        """
        os.makedirs(self.__symbol_folder, exist_ok=True)
        os.makedirs(self.__aliases_folder, exist_ok=True)
        os.makedirs(self.__comments_folder, exist_ok=True)
        for name, sym in self.__symbols.items():
            with open(self.__get_pickle_path(self.__symbol_folder, name, True), 'wb') as _:
                pickle.dump(sym, _)
        for name, aliases in self.__aliases.items():
            if aliases:
                with open(self.__get_pickle_path(self.__aliases_folder, name, True), 'wb') as _:
                    pickle.dump(aliases, _)
        for name, comment in self.__comments.items():
            if comment:
                with open(self.__get_pickle_path(self.__comments_folder, name, True), 'wb') as _:
                    pickle.dump(comment, _)

    def __get_aliases(self, name):
        return self.__aliases.get(name, [])

    # pylint: disable=unused-argument
    def get_symbol(self, name, prefer_class=False):
        """
        Banana banana
        """
        return self.__symbols.get(name)
