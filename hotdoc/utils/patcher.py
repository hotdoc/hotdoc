import codecs
import commands

class Patcher(object):
    def patch (self, filename, begin, end, new_comment):
        file_encoding = commands.getoutput('file -b --mime-encoding %s' %
                filename)
        with codecs.open(filename, 'r', file_encoding) as f:
            lines = f.readlines()

        res = lines[0:begin] + [new_comment + '\n'] + lines[end:]
        res = ''.join(res)
        with open (filename, 'w') as f:
            f.write(res)
