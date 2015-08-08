from doxygen_parser.doxygen_parser import parse_comment_block

def parse_doxygen_comment (raw_comment):
    block = parse_comment_block (raw_comment)
    return block
