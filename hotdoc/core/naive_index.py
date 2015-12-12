import os
import shutil

# FIXME: be less naive :)
class NaiveIndexFormatter(object):
    def __init__(self, symbols, directory='tmp_markdown_files',
            index_name='tmp-index.markdown'):
        pages = {}

        for name, symbol in symbols.iteritems():
            filename = symbol.filename
            if filename is None:
                continue
            page_symbols = pages.get(filename)
            if not page_symbols:
                page_symbols = []
                pages[filename] = page_symbols
            page_symbols.append (name)

        mddir = directory

        try:
            shutil.rmtree (mddir)
        except OSError as e:
            pass

        try:
            os.mkdir (mddir)
        except OSError:
            pass

        with open (os.path.join (mddir, index_name), 'w') as index:
            for page, symbols in pages.iteritems():
                base_name = os.path.basename (os.path.splitext(page)[0])
                filename = '%s.markdown' % base_name
                index.write ('#### [%s](%s)\n' % (base_name, filename))
                with open (os.path.join(mddir, filename), 'a') as f:
                    for symbol in symbols:
                        f.write('* [%s]()\n' % symbol)
