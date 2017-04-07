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

# pylint: disable=import-error
from sqlalchemy import create_engine, Column, Integer, String
# pylint: disable=import-error
from sqlalchemy.orm import sessionmaker

from hotdoc.core.symbols import Symbol

from hotdoc.utils.alchemy import Base
from hotdoc.utils.signals import Signal
from hotdoc.utils.loggable import debug


# pylint: disable=too-few-public-methods
class ProxySymbol(Base):
    """A proxy type to handle aliased symbols"""
    __tablename__ = 'proxy_symbols'

    id_ = Column(Integer, primary_key=True)
    target = Column(String)
    unique_name = Column(String)


# pylint: disable=too-many-instance-attributes
class Database(object):
    """
    A store of comments and symbols. Eventually, during the documentation
    generation phase, comments and symbols are matched up (using
    `hotdoc.core.comment.Comment.name` and
    `hotdoc.core.symbol.Symbol.unique_name`) to determine what goes into the
    generated documentation and how it is described.
    """
    def __init__(self):
        self.comment_added_signal = Signal()
        self.comment_updated_signal = Signal()

        self.__comments = {}
        self.__symbols = {}
        self.__incremental = False
        self.__session = None
        self.__engine = None
        self.__aliases = {}

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
            self.__session.add(symbol)
            debug('Created symbol with unique name %s' % unique_name,
                  'symbols')

        for key, value in list(kwargs.items()):
            setattr(symbol, key, value)

        self.__symbols[unique_name] = symbol
        for alias in aliases:
            self.__symbols[alias] = symbol
        self.__aliases[unique_name] = aliases

        return symbol

    def __get_aliases(self, name):
        aliases = self.__aliases.get(name, [])

        if aliases or not self.__incremental:
            return aliases

        proxies = self.__session.query(ProxySymbol).filter(
            ProxySymbol.unique_name == name)

        for proxy in proxies:
            aliases.append(proxy.unique_name)

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
            sym = self.__session.query(Symbol).filter(Symbol.unique_name ==
                                                      name).first()

        if not sym:
            sym = self.__session.query(ProxySymbol).filter(
                ProxySymbol.unique_name == name).first()
            sym = self.get_symbol(sym.target)

        if sym:
            # Faster look up next time around
            self.__symbols[name] = sym
        return sym

    def setup(self, db_folder):
        """
        Banana banana
        """
        db_path = os.path.join(db_folder, 'hotdoc.db')

        if os.path.exists(db_path):
            self.__incremental = True

        self.__engine = create_engine('sqlite:///%s' % db_path)
        self.__session = sessionmaker(self.__engine)()
        self.__session.autoflush = False
        Base.metadata.create_all(self.__engine)

    def flush(self):
        """
        Banana banana
        """
        self.__session.flush()

    def persist(self):
        """
        Banana banana
        """
        self.__session.commit()

    def close(self):
        """
        Banana banana
        """
        self.__session.close()

    def get_session(self):
        """
        Banana banana
        """
        return self.__session

    def __update_symbol_comment(self, comment):
        self.comment_updated_signal(self, comment)
