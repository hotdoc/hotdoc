import os
import cPickle as pickle
from datetime import datetime
from hotdoc.core.alchemy_integration import MutableObject

import traceback

class Link (MutableObject):
    def __init__(self, ref, title, id_):
        self.title = title
        self.ref = ref
        self.id_ = id_
        MutableObject.__init__(self)

    def get_link (self):
        return self.ref


class LinkResolver(object):
    def __init__(self):
        self.__links = {}

    def get_named_link (self, name):
        return self.__links.get (name)

    def add_link (self, link):
        if not link.id_ in self.__links:
            self.__links[link.id_] = link
