import os
import cPickle as pickle
from datetime import datetime
from hotdoc.core.alchemy_integration import MutableObject

import traceback

class Link (MutableObject):
    def __init__(self, ref, title, id_):
        self._title = title
        self.ref = ref
        self.id_ = id_
        MutableObject.__init__(self)

    def get_link (self):
        return self.ref

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, title):
        self._title = title

class LinkResolver(object):
    def __init__(self):
        self.__links = {}

    def get_named_link (self, name):
        return self.__links.get (name)

    def add_link (self, link):
        if not link.id_ in self.__links:
            self.__links[link.id_] = link

    def dump(self):
        pickle.dump(self.__links, open('hd_links.p', 'wb'))

    def load(self):
        self.__links = pickle.load(open('hd_links.p', 'rb'))
