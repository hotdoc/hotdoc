from doxygen_parser.doxygen_parser import parse_comment_block

class DoxygenRawCommentParser (object):
    def parse_comment (raw_comment, filename):
        block = parse_comment_block (raw_comment)
        return block
