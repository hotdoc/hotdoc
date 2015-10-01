import sys, re
from itertools import izip_longest
from datetime import datetime
from hotdoc.core.comment_block import *

#http://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return izip_longest(*args, fillvalue=fillvalue)

class GtkDocRawCommentParser (object):
    def __init__(self):
        """
        Lifted from
        http://stackoverflow.com/questions/5323703/regex-how-to-match-sequence-of-key-value-pairs-at-end-of-string
        """
        self.kv_regex = re.compile(r'''
                                   [\S]+=
                                   (?:
                                   \s*
                                   (?!\S+=)\S+
                                   )+
                                   ''', re.VERBOSE)

    def parse_title (self, title):
        split = title.split (': ', 1)
        title = split[0].rstrip(':')
        annotations = []
        if len (split) > 1:
            annotations = self.parse_annotations (split[1])
        return title, annotations

    def parse_key_value_annotation (self, name, string):
        arg = {}
        kvs = self.kv_regex.findall (string)
        kvs = dict([kv.split('=', 1) for kv in kvs])
        return GtkDocAnnotation (name, kvs)

    def parse_annotation (self, string):
        split = string.split ()
        name = split[0].strip()
        if len (split) == 1:
            return GtkDocAnnotation (name, None)
        elif '=' in split[1]:
            return self.parse_key_value_annotation (name, split[1])
        else:
            return GtkDocAnnotation (name, [split[1]])

    def parse_annotations (self, string):
        parsed_annotations = []
        par_level = 0
        current_annotation = ""
        for c in string:
            if c == '(':
                par_level += 1
            elif c == ')':
                par_level -= 1

            if par_level > 1:
                return []
            elif par_level == 1 and c not in '()':
                current_annotation += c
            elif par_level == 0:
                if c not in ' \t\n\r()':
                    return []
                if current_annotation:
                    ann = self.parse_annotation (current_annotation)
                    if ann:
                        parsed_annotations.append (ann)
                    current_annotation = ""
            elif par_level < 0:
                return []

        if par_level != 0:
            return []

        return parsed_annotations

    def extract_annotations (self, desc):
        split = desc.split (': ', 1)

        if len (split) == 1:
            return desc, []

        annotations = self.parse_annotations (split[0])
        if not annotations:
            return desc, []

        return split[1].strip(), annotations

    def parse_parameter (self, name, desc):
        name = name.strip()[1:-1].strip()
        desc = desc.strip()
        desc, annotations = self.extract_annotations (desc)
        return GtkDocParameter (name, annotations, desc)

    def parse_title_and_parameters (self, tp):
        tps = re.split (r'(\n[ \t]*@[\S]+[ \t]*:)', tp)
        title, annotations = self.parse_title (tps[0])
        parameters = []
        for name, desc in grouper (tps[1:], 2):
            parameters.append (self.parse_parameter (name, desc))
        return title, parameters, annotations

    def parse_since_tag (self, name, desc):
        return GtkDocTag (name, desc, [], None)

    def parse_returns_tag (self, name, desc):
        desc, annotations = self.extract_annotations (desc)
        return GtkDocTag (name, None, annotations, desc)

    def parse_tag (self, name, desc):
        if name.lower() == "since":
            return self.parse_since_tag (name, desc)
        elif name.lower() == "returns":
            return self.parse_returns_tag (name, desc)
        print ("What the hell dude")

    def parse_description_and_tags (self, dt):
        dts = re.split (r'((?:^|\n)[ \t]*(returns|Returns|since|Since):)', dt)
        tags = []

        desc = dts[0]
        if len (dts) == 1:
            return desc, tags

        for raw, name, tag_desc in grouper (dts[1:], 3):
            tags.append (self.parse_tag (name.strip(), tag_desc.strip()))

        return desc, tags

    def strip_comment (self, comment):
        comment = re.sub ('^[\W]*\/[\*]+[\W]*', '', comment)
        comment = re.sub ('\*\/[\W]*$', '', comment)
        comment = re.sub ('\n[ \t]*\*', '\n', comment)
        return comment.strip()

    def parse_comment (self, comment, filename, lineno, stripped=False):
        if not stripped:
            comment = self.strip_comment (comment)

        split = re.split (r'\n[\W]*\n', comment, maxsplit=1)
        block_name, parameters, annotations = self.parse_title_and_parameters (split[0])
        description = ""
        tags = []
        if len (split) > 1:
            description, tags = self.parse_description_and_tags (split[1])
        block = GtkDocCommentBlock (block_name, filename, lineno, annotations, parameters,
                description, tags)
        return block

if __name__ == "__main__":
    dp = GtkDocRawCommentParser()
    with open (sys.argv[1], 'r') as f:
        c = f.read()
        n = datetime.now()
        block = dp.parse_comment (c, sys.argv[1], 0)
