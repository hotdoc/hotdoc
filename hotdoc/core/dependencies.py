import os
import pickle

class DependencyNode (object):
    def __init__(self, filename):
        self.__children = set ({})
        self.__parents = set({})
        self.filename = filename
        self.mtime = os.path.getmtime (filename)
        self.is_stale = False

    def add_child (self, child):
        self.__children.add (child)
        child.__add_parent (self)

    def __add_parent (self, parent):
        self.__parents.add (parent)

    def get_children (self):
        return self.__children

    def get_parents (self):
        return self.__parents

    def set_stale (self, is_stale):
        self.is_stale = is_stale
        if not is_stale:
            self.mtime = os.path.getmtime (self.filename)
        else:
            for child in self.__children:
                child.set_stale (is_stale)


class DependencyTree (object):
    def __init__(self, pickled_filename, source_filenames):
        self.initial = True
        if os.path.exists (pickled_filename):
            self.root_nodes = pickle.load (open (pickled_filename, 'rb'))
            self.stale_sources = set ({})
            self.initial = False
        else:
            self.stale_sources = set(source_filenames)
            self.root_nodes = {}

        self.filename = pickled_filename
        self.all_nodes = {}

        self.stale_sections = {}
        if not self.initial:
            self.check_stale_nodes (self.root_nodes.itervalues())
            for name, node in self.all_nodes.iteritems():
                if node.is_stale:
                    if name in source_filenames:
                        self.stale_sources.add (name)
                    else:
                        self.stale_sections[name] = node

        stale = []
        for filename in source_filenames:
            self.add_dependency (None, filename)
            if filename in self.stale_sources:
                stale.append (filename)

        self.stale_sources = stale

    def __mark_stale_nodes (self, node):
        parents = node.get_parents()
        node.set_stale (True)

        for p in parents:
            self.__mark_stale_nodes (p)

    def check_stale_nodes (self, nodes):
        for node in nodes:
            if os.path.getmtime (node.filename) > node.mtime:
                self.__mark_stale_nodes (node)

            self.all_nodes[node.filename] = node
            self.check_stale_nodes (node.get_children())

    def __get_or_create_node (self, filename, depended_on=False):
        filename = os.path.abspath (filename)
        node = self.all_nodes.get (filename)
        if not node:
            node = DependencyNode (filename)
            self.all_nodes[filename] = node 
        if not depended_on:
            self.root_nodes[filename] = node
        return node

    def add_dependency (self, depending, depended_on, unmark_stale=True):
        if depended_on:
            depended_on_node = self.__get_or_create_node (depended_on,
                    depended_on=True)

        if depending:
            depending_node = self.__get_or_create_node (depending)
            if depended_on:
                depending_node.add_child (depended_on_node)

        if unmark_stale:
            if depended_on:
                depended_on_node.set_stale(False)
            if depending:
                depending_node.set_stale(False)

    def dump (self):
        pickle.dump (self.root_nodes, open (self.filename, 'wb'))
