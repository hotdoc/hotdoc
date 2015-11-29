from hotdoc.core.alchemy_integration import MutableObject

class Link (MutableObject):
    def __init__(self, ref, title, id_):
        self.title = title
        self.ref = ref
        self.id_ = id_
        MutableObject.__init__(self)

    def get_link (self):
        return self.ref

class LinkResolver(object):
    def __init__(self, doc_tool):
        self.__links = {}
        self.__external_links = {}
        self.doc_tool = doc_tool
        self.__translated_names = {}

    # Kind of gi-specific, but can't really hurt
    def set_translated_names(self, names):
        self.__translated_names = names

    def translate(self, link):
        if not link:
            return None

        link.title = self.__translated_names.get(link.id_, link.title)
        return link

    def get_named_link (self, name):
        if name in self.__links:
            return self.translate(self.__links[name])

        sym = self.doc_tool.get_symbol(name)
        if sym:
            self.__links[name] = sym.link
            return self.translate(sym.link)

        if name in self.__external_links:
            self.__links[name] = self.__external_links[name]
            return self.translate(self.__links[name])

        self.__links[name] = None
        return None

    def add_link (self, link):
        if not link.id_ in self.__links:
            self.__links[link.id_] = link

    def upsert_link (self, link, overwrite_ref=False, external=False):
        elink = self.__links.get (link.id_)

        if elink and external:
            return elink

        if external:
            self.__external_links[link.id_] = link
            return link

        if elink:
            if elink.ref is None or overwrite_ref and link.ref:
                elink.ref = link.ref
            if link.title is not None:
                elink.title = link.title
            return elink
        self.add_link (link)
        return link
