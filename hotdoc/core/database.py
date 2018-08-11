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
from hotdoc.core.symbols import Symbol
from hotdoc.utils.signals import Signal
from hotdoc.utils.loggable import debug


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
        self.comment_updated_signal = Signal()

        self.__comments = {}
        self.__symbols = {}
        self.__aliases = {}
        self.__symbol_folder = os.path.join(private_folder or '/tmp',
                                            "symbols")
        self.__aliases_folder = os.path.join(private_folder or '/tmp',
                                             "aliases")
        self.__comments_folder = os.path.join(private_folder or '/tmp',
                                              "comments")
        self.__incremental = os.path.exists(self.__symbol_folder) and \
            os.path.exists(self.__aliases_folder)

    def add_comment(self, comment):
        """
        Add a comment to the database.

        Args:
            comment (hotdoc.core.Comment): comment to add
        """
        if not comment:
            return

        self.__comments[comment.name] = comment
        if self.__incremental:
            self.__update_symbol_comment(comment)
        else:
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

        if self.__incremental:
            fname = self.__get_pickle_path(self.__comments_folder, name)
            if os.path.exists(fname):
                with open(fname, 'rb') as _:
                    self.__comments[name] = pickle.load(_)
                    return self.__comments[name]

        return None

    def get_or_create_symbol(self, type_, **kwargs):
        """
        Banana banana
        """
        unique_name = kwargs.get('unique_name')
        if not unique_name:
            unique_name = kwargs.get('display_name')
            kwargs['unique_name'] = unique_name

        filename = kwargs.get('filename')
        if filename:
            kwargs['filename'] = os.path.abspath(filename)

        aliases = kwargs.pop('aliases', [])
        for alias in aliases:
            self.get_or_create_symbol(ProxySymbol,
                                      unique_name=alias,
                                      target=unique_name)

        if self.__incremental:
            symbol = self.get_symbol(unique_name)
        else:
            symbol = None

        if not symbol:
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
        aliases = self.__aliases.get(name, [])

        if not self.__incremental:
            return aliases

        if not aliases:
            path = self.__get_pickle_path(self.__aliases_folder, name)
            if os.path.exists(path):
                with open(path, 'rb') as _:
                    aliases = pickle.load(_)

        if aliases:
            # Faster look up next time around
            self.__aliases[name] = aliases

        return aliases

    # pylint: disable=unused-argument
    def get_symbol(self, name, prefer_class=False):
        """
        Banana banana
        """
        sym = self.__symbols.get(name)

        if not self.__incremental:
            return sym

        if not sym:
            path = os.path.join(self.__symbol_folder, name)
            if os.path.exists(path):
                with open(path, 'rb') as _:
                    sym = pickle.load(_)

        if sym:
            # Faster look up next time around
            self.__symbols[name] = sym
            if isinstance(sym, ProxySymbol):
                return self.get_symbol(sym.target)

        return sym

    def __update_symbol_comment(self, comment):
        self.comment_updated_signal(self, comment)
