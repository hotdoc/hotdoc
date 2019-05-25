import os
from lxml import etree
from hotdoc.extensions.gi.utils import DATADIR
from hotdoc.utils.loggable import info


GTKDOC_HREFS = {}


def parse_devhelp_index(dir_):
    path = os.path.join(dir_, os.path.basename(dir_) + '.devhelp2')
    if not os.path.exists(path):
        return False

    dh_root = etree.parse(path).getroot()
    online = dh_root.attrib.get('online')
    name = dh_root.attrib.get('name')
    author = dh_root.attrib.get('author')
    if not online:
        if not name:
            return False
        online = 'https://developer.gnome.org/%s/unstable/' % name

    keywords = dh_root.findall('.//{http://www.devhelp.net/book}keyword')
    for kw in keywords:
        name = kw.attrib["name"]
        type_ = kw.attrib['type']
        link = kw.attrib['link']

        if type_ in ['macro', 'function']:
            name = name.rstrip(u' ()')
        elif type_ in ['struct', 'enum', 'union']:
            split = name.split(' ', 1)
            if len(split) == 2:
                name = split[1]
            else:
                name = split[0]
        elif type_ in ['signal', 'property']:
            anchor = link.split('#', 1)[1]
            if author == 'hotdoc':
                name = anchor
            else:
                split = anchor.split('-', 1)
                if type_ == 'signal':
                    name = '%s::%s' % (split[0], split[1].lstrip('-'))
                else:
                    name = '%s:%s' % (split[0], split[1].lstrip('-'))
        elif type_ in ['vfunc']:
            anchor = link.split('#', 1)[1]
            if author == 'hotdoc':
                name = anchor
                GTKDOC_HREFS[name.replace('::', '.')] = online + link

        GTKDOC_HREFS[name] = online + link

    return True


def parse_sgml_index(dir_):
    remote_prefix = ""
    n_links = 0
    path = os.path.join(dir_, "index.sgml")
    with open(path, 'r') as f:
        for l in f:
            if l.startswith("<ONLINE"):
                remote_prefix = l.split('"')[1]
            elif not remote_prefix:
                break
            elif l.startswith("<ANCHOR"):
                split_line = l.split('"')
                filename = split_line[3].split('/', 1)[-1]
                title = split_line[1].replace('-', '_')

                if title.endswith(":CAPS"):
                    title = title [:-5]
                if remote_prefix:
                    href = '%s/%s' % (remote_prefix, filename)
                else:
                    href = filename

                GTKDOC_HREFS[title] = href
                n_links += 1


def gather_gtk_doc_links ():
    for envvar in ('XDG_DATA_DIRS', 'XDG_DATA_HOME'):
        for datadir in os.environ.get(envvar, '').split(os.pathsep):
            for path in (os.path.join(datadir, 'devhelp', 'books'), os.path.join(datadir, 'gtk-doc', 'html')):
                if not os.path.exists(path):
                    info("no gtk doc to gather links from in %s" % path)
                    continue

                for node in os.listdir(path):
                    dir_ = os.path.join(path, node)
                    if os.path.isdir(dir_):
                        if not parse_devhelp_index(dir_):
                            try:
                                parse_sgml_index(dir_)
                            except IOError:
                                pass


gather_gtk_doc_links()
