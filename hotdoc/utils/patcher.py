"""
Banana banana
"""
import codecs
import commands


# pylint: disable=too-few-public-methods
class Patcher(object):
    """
    Banana banana
    """
    # pylint: disable=no-self-use
    def patch(self, filename, begin, end, new_comment):
        """
        Banana banana
        """
        file_encoding = commands.getoutput('file -b --mime-encoding %s' %
                                           filename)
        with codecs.open(filename, 'r', file_encoding) as _:
            lines = _.readlines()

        res = lines[0:begin] + [new_comment + '\n'] + lines[end:]
        res = ''.join(res)
        with open(filename, 'w') as _:
            _.write(res)
