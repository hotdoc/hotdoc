import os

class Link (object):
    def get_link (self):
        raise NotImplementedError

class ExternalLink (Link):
    def __init__ (self, symbol, local_prefix, remote_prefix, filename, title):
        self.symbol = symbol
        self.local_prefix = local_prefix
        self.remote_prefix = remote_prefix
        self.filename = filename
        self.title = title

    def get_link (self):
        return "%s/%s" % (self.remote_prefix, self.filename)


class LocalLink (Link):
    def __init__(self, id_, pagename, title):
        self.id_ = id_
        self.pagename = pagename
        self.title = title

    def get_link (self):
        if (self.id_):
            return "%s#%s" % (self.pagename, self.id_)
        else:
            return self.pagename


class LinkResolver(object):
    def __init__(self):
        self.__external_links = {}
        self.__local_links = {}
        self.__gather_gtk_doc_links ()

    def get_named_link (self, name):
        link = None
        try:
            link = self.__local_links[name]
        except KeyError:
            try:
                link = self.__external_links[name]
            except KeyError:
                pass
        return link

    def add_local_link (self, link):
        self.__local_links[link.title] = link

    def __gather_gtk_doc_links (self):
        if not os.path.exists(os.path.join("/usr/share/gtk-doc/html")):
            print "no gtk doc to look at"
            return

        for node in os.listdir(os.path.join(DATADIR, "gtk-doc", "html")):
            dir_ = os.path.join(DATADIR, "gtk-doc/html", node)
            if os.path.isdir(dir_) and not "gst" in dir_:
                try:
                    self.__parse_sgml_index(dir_)
                except IOError:
                    pass

    def __parse_sgml_index(self, dir_):
        symbol_map = dict({})
        remote_prefix = ""
        with open(os.path.join(dir_, "index.sgml"), 'r') as f:
            for l in f:
                if l.startswith("<ONLINE"):
                    remote_prefix = l.split('"')[1]
                elif l.startswith("<ANCHOR"):
                    split_line = l.split('"')
                    filename = split_line[3].split('/', 1)[-1]
                    title = split_line[1].replace('-', '_')
                    link = ExternalLink (split_line[1], dir_, remote_prefix,
                            filename, title)
                    if title.endswith (":CAPS"):
                        title = title [:-5]
                    self.__external_links[title] = link

link_resolver = LinkResolver()
