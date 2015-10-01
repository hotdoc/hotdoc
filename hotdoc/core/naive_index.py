import os
from pprint import pprint

class NaiveIndexFormatter(object):
    def __init__(self, symbols):
        pages = {}
        for name, symbol in symbols.iteritems():
            filename = str(symbol.location.file)
            page_symbols = pages.get(filename)
            if not page_symbols:
                page_symbols = []
                pages[filename] = page_symbols
            page_symbols.append (name)

        mddir = "tmp_markdown_files"

        try:
            os.rmdir (mddir)
        except OSError:
            pass

        try:
            os.mkdir (mddir)
        except OSError:
            pass

        with open (os.path.join (mddir, "tmp_index.markdown"), 'w') as index:
            for page, symbols in pages.iteritems():
                base_name = os.path.basename (os.path.splitext(page)[0])
                filename = '%s.markdown' % base_name
                index.write ('#### [%s](%s)\n' % (base_name, filename))
                with open (os.path.join(mddir, filename), 'a') as f:
                    for symbol in symbols:
                        f.write('* [%s]()\n' % symbol)
