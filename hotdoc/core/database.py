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
import json

from collections import defaultdict, OrderedDict

# pylint: disable=import-error
# pylint: disable=import-error
from hotdoc.core.exceptions import HotdocException
from hotdoc.core.symbols import Symbol, ProxySymbol
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


def serialize(obj):
    try:
        return obj.__getstate__()
    except AttributeError:
        return obj.__dict__


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

        self.__comments = OrderedDict()
        self.__symbols = OrderedDict()
        self.__aliased = defaultdict(list)
        self.__aliases = OrderedDict()
        self.__private_folder = private_folder or '/tmp'

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

        if unique_name in self.__symbols and not type_ == ProxySymbol:
            warn('symbol-redefined', "%s(unique_name=%s, filename=%s, project=%s)"
                 " has already been defined: %s" % (type_.__name__, unique_name, filename,
                                                    kwargs.get('project_name'),
                                                    self.get_symbol(unique_name)))
            return None

        aliases = kwargs.pop('aliases', [])
        alias_symbols = []
        for alias in aliases:
            alias_symbols.append(
                self.create_symbol(ProxySymbol,
                unique_name=alias,
                target=unique_name))

        symbol = type_()
        debug('Created symbol with unique name %s' % unique_name,
              'symbols')

        for key, value in list(kwargs.items()):
            setattr(symbol, key, value)
        symbol.aliases += alias_symbols

        if not isinstance(symbol, ProxySymbol):
            self.__symbols[unique_name] = symbol
        self.__aliased[unique_name].extend(aliases)

        for alias in self.__aliased[unique_name]:
            self.__aliases[alias] = symbol

        return symbol

    def rename_symbol(self, unique_name, target):
        sym = self.__symbols.get(target)
        if sym:
            for alias in self.__aliased[unique_name]:
                alias.target = unique_name
            if sym.unique_name == sym.display_name:
                sym.display_name = unique_name
            sym.unique_name = unique_name
            del self.__symbols[target]
            self.__symbols[unique_name] = sym
            debug('Renamed symbol with unique name %s to %s' % (target, unique_name))
        return sym

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
        # Let's try and use the name of the symbols comments ended up
        # associated with as the keys
        resolved_comments = OrderedDict()

        for name, comment in self.__comments.items():
            if comment:
                sym = self.get_symbol(name)
                if sym:
                    resolved_comments[sym.unique_name] = comment
                else:
                    resolved_comments[name] = comment

        with open(os.path.join(self.__private_folder, 'all_comments.json'), 'w', encoding='utf8') as f:
            f.write(json.dumps(resolved_comments, default=serialize, indent=2))

        with open(os.path.join(self.__private_folder, 'symbol_index.json'), 'w', encoding='utf8') as f:
            f.write(json.dumps(list(self.get_all_symbols().keys()), default=serialize, indent=2))

    def __get_aliases(self, name):
        return self.__aliased[name]

    # pylint: disable=unused-argument
    def get_symbol(self, name, prefer_class=False):
        """
        Banana banana
        """
        if name in self.__symbols:
            return self.__symbols.get(name)

        return self.__aliases.get(name)

    def get_all_symbols(self):
        return self.__symbols