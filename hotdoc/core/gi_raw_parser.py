import sys, re
from itertools import izip_longest
from hotdoc.core.comment_block import *

#http://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return izip_longest(*args, fillvalue=fillvalue)

class GtkDocRawCommentParser (object):
    def __init__(self, doc_tool):
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
        self.doc_tool = doc_tool

        tag_validation_regex = r'((?:^|\n)[ \t]*('
        tag_validation_regex += 'returns|Returns|since|Since|deprecated|Deprecated|stability|Stability|Return value'
        for validator in doc_tool.tag_validators.values():
            tag_validation_regex += '|%s|%s' % (validator.name,
                    validator.name.lower())
        tag_validation_regex += '):)'

        self.tag_validation_regex = re.compile (tag_validation_regex)

    def parse_title (self, raw_title):
        # Section comments never contain annotations,
        # We also normalize them here to not contain any spaces.
        # FIXME: This code now only lives here for the purpose of gtk-doc conversion
        # Could remove that one day
        if "SECTION" in raw_title:
            return ''.join(raw_title.split(' ')), []

        split = raw_title.split (': ', 1)
        title = split[0].rstrip(':')
        annotations = []
        if len (split) > 1:
            annotations = self.parse_annotations (split[1])
        elif not raw_title.strip().endswith(':'):
            print "Missing colon in comment name :", raw_title
            return None, []
        return title, annotations

    def parse_key_value_annotation (self, name, string):
        arg = {}
        kvs = self.kv_regex.findall (string)
        kvs = dict([kv.split('=', 1) for kv in kvs])
        return Annotation (name=name, argument=kvs)

    def parse_annotation (self, string):
        split = string.split ()
        name = split[0].strip()
        if len (split) == 1:
            return Annotation (name=name)
        elif '=' in split[1]:
            return self.parse_key_value_annotation (name, split[1])
        else:
            return Annotation (name=name, argument=[split[1]])

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
        annotations = {annotation.name: annotation for annotation in
                annotations}
        return Comment (name=name, annotations=annotations,
                description=desc)

    def parse_title_and_parameters (self, tp):
        tps = re.split (r'(\n[ \t]*@[\S]+[ \t]*:)', tp)
        title, annotations = self.parse_title (tps[0])
        parameters = []
        for name, desc in grouper (tps[1:], 2):
            parameters.append (self.parse_parameter (name, desc))
        return title, parameters, annotations

    def parse_since_tag (self, name, desc):
        return Tag (name=name, description=desc)

    def parse_deprecated_tag (self, name, desc):
        return Tag (name=name, description=desc)

    def parse_stability_tag (self, name, desc):
        return Tag (name=name, description=desc)

    def parse_returns_tag (self, name, desc):
        desc, annotations = self.extract_annotations (desc)
        annotations = {annotation.name: annotation for annotation in
                annotations}
        return Tag (name=name, annotations=annotations, description=desc)

    def parse_tag (self, name, desc):
        if name.lower() == "since":
            return self.parse_since_tag (name, desc)
        elif name.lower() == "returns":
            return self.parse_returns_tag (name, desc)
        elif name.lower() == "return value":
            return self.parse_returns_tag ("returns", desc)
        elif name.lower() == "stability":
            return self.parse_stability_tag ("stability", desc)
        elif name.lower() == "deprecated":
            return self.parse_deprecated_tag("deprecated", desc)
        else:
            validator = self.doc_tool.tag_validators.get(name)
            if not validator:
                print "FIXME no tag validator"
                return None
            if not validator.validate(desc):
                print "invalid value for tag %s : %s" % name, desc
                return None
            return Tag(name=name, description=desc)

    def parse_description_and_tags (self, dt):
        dts = self.tag_validation_regex.split(dt)
        tags = []

        desc = dts[0]
        if len (dts) == 1:
            return desc, tags

        for raw, name, tag_desc in grouper (dts[1:], 3):
            tag = self.parse_tag (name.strip(), tag_desc.strip())
            if tag:
                tags.append(tag)

        return desc, tags

    def strip_comment (self, comment):
        comment = re.sub ('^[\W]*\/[\*]+[\W]*', '', comment)
        comment = re.sub ('\*\/[\W]*$', '', comment)
        comment = re.sub ('\n[ \t]*\*', '\n', comment)
        return comment.strip()

    def validate_c_comment(self, comment):
        return re.match(r'(/\*\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)$',
                comment) is not None

    def parse_comment (self, comment, filename, lineno, endlineno, stripped=False):
        if not stripped and not comment.lstrip().startswith ('/**'):
            return None

        if not self.validate_c_comment(comment.strip()):
            return None

        raw_comment = comment
        comment = unicode(comment.encode('utf8'))
        if not stripped:
            comment = self.strip_comment (comment)

        comment = unicode(comment.encode('utf8'))

        split = re.split (r'\n[\W]*\n', comment, maxsplit=1)
        block_name, parameters, annotations = self.parse_title_and_parameters (split[0])

        if not block_name:
            return None

        description = ""
        tags = []
        if len (split) > 1:
            description, tags = self.parse_description_and_tags (split[1])

        title = None
        short_description = None
        actual_parameters = {}
        for param in parameters:
            if param.name.lower() == 'short_description':
                short_description = param.description
            elif param.name.lower() == 'title':
                title = param.description
            else:
                actual_parameters[param.name] = param

        annotations = {annotation.name: annotation for annotation in
                annotations}
        tags = {tag.name.lower(): tag for tag in tags}

        block = Comment (name=block_name, filename=filename, lineno=lineno,
                endlineno=endlineno,
                annotations=annotations, params=actual_parameters,
                description = description, short_description=short_description,
                title=title, tags=tags, raw_comment=raw_comment)

        return block

if __name__ == "__main__":
    dp = GtkDocRawCommentParser()
    with open (sys.argv[1], 'r') as f:
        c = f.read()
        block = dp.parse_comment (c, sys.argv[1], 0)
