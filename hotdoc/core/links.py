import os
import cPickle as pickle
from datetime import datetime

import traceback

class Link (object):
    def __init__(self, ref, title, id_):
        self.title = title
        self.ref = ref
        self.id_ = id_

    def get_link (self):
        return self.ref


class LinkResolver(object):
    def __init__(self):
        self.__links = {}

    def unpickle (self, output):
        n = datetime.now()
        try:
            links = pickle.load (open (os.path.join (output, "links.p"), 'rb'))
        except IOError:
            return

        self.__links = links

    def pickle (self, output):
        n = datetime.now()
        pickle.dump (self.__links,
                open (os.path.join (output, "links.p"), 'wb'))

    def get_named_link (self, name):
        return self.__links.get (name)

    def add_link (self, link):
        if not link.id_ in self.__links:
            self.__links[link.id_] = link
