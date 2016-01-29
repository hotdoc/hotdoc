"""
Banana banana
"""

import re
from itertools import izip_longest

from hotdoc.core.comment_block import Comment, Annotation, Tag
from hotdoc.core.file_includer import add_md_includes


# http://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
def _grouper(iterable, n_args, fillvalue=None):
    """
    Banana banana
    """
    args = [iter(iterable)] * n_args
    return izip_longest(*args, fillvalue=fillvalue)


# pylint: disable=too-few-public-methods
class GtkDocRawCommentParser(object):
    """
    Banana banana
    """

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
        tag_validation_regex += 'returns|Returns|since|Since|deprecated'\
            '|Deprecated|stability|Stability|Return value'
        for validator in doc_tool.tag_validators.values():
            tag_validation_regex += '|%s|%s' % (validator.name,
                                                validator.name.lower())
        tag_validation_regex += '):)'

        self.tag_validation_regex = re.compile(tag_validation_regex)

    def __parse_title(self, raw_title):
        # Section comments never contain annotations,
        # We also normalize them here to not contain any spaces.
        # FIXME: This code now only lives here for the purpose of
        # gtk-doc conversion
        # Could remove that one day
        if "SECTION" in raw_title:
            return ''.join(raw_title.split(' ')), []

        split = raw_title.split(': ', 1)
        title = split[0].rstrip(':')
        annotations = []
        if len(split) > 1:
            annotations = self.__parse_annotations(split[1])
        elif not raw_title.strip().endswith(':'):
            print "Missing colon in comment name :", raw_title
            return None, []
        return title, annotations

    def __parse_key_value_annotation(self, name, string):
        kvs = self.kv_regex.findall(string)
        kvs = dict([kv.split('=', 1) for kv in kvs])
        return Annotation(name=name, argument=kvs)

    def __parse_annotation(self, string):
        split = string.split()
        name = split[0].strip()
        if len(split) == 1:
            return Annotation(name=name)
        elif '=' in split[1]:
            return self.__parse_key_value_annotation(name, split[1])
        else:
            return Annotation(name=name, argument=[split[1]])

    def __parse_annotations(self, string):
        parsed_annotations = []
        par_level = 0
        current_annotation = ""
        for _ in string:
            if _ == '(':
                par_level += 1
            elif _ == ')':
                par_level -= 1

            if par_level > 1:
                return []
            elif par_level == 1 and _ not in '()':
                current_annotation += _
            elif par_level == 0:
                if _ not in ' \t\n\r()':
                    return []
                if current_annotation:
                    ann = self.__parse_annotation(current_annotation)
                    if ann:
                        parsed_annotations.append(ann)
                    current_annotation = ""
            elif par_level < 0:
                return []

        if par_level != 0:
            return []

        return parsed_annotations

    def __extract_annotations(self, desc):
        split = desc.split(': ', 1)

        if len(split) == 1:
            return desc, []

        annotations = self.__parse_annotations(split[0])
        if not annotations:
            return desc, []

        return split[1].strip(), annotations

    def __parse_parameter(self, name, desc):
        name = name.strip()[1:-1].strip()
        desc = desc.strip()
        desc, annotations = self.__extract_annotations(desc)
        annotations = {annotation.name: annotation for annotation in
                       annotations}
        return Comment(name=name, annotations=annotations,
                       description=desc)

    def __parse_title_and_parameters(self, title_and_params):
        tps = re.split(r'(\n[ \t]*@[\S]+[ \t]*:)', title_and_params)
        title, annotations = self.__parse_title(tps[0])
        parameters = []
        for name, desc in _grouper(tps[1:], 2):
            parameters.append(self.__parse_parameter(name, desc))
        return title, parameters, annotations

    # pylint: disable=no-self-use
    def __parse_since_tag(self, name, desc):
        return Tag(name=name, description=desc)

    # pylint: disable=no-self-use
    def __parse_deprecated_tag(self, name, desc):
        return Tag(name=name, description=desc)

    # pylint: disable=no-self-use
    def __parse_stability_tag(self, name, desc):
        return Tag(name=name, description=desc)

    # pylint: disable=no-self-use
    def __parse_returns_tag(self, name, desc):
        desc, annotations = self.__extract_annotations(desc)
        annotations = {annotation.name: annotation for annotation in
                       annotations}
        return Tag(name=name, annotations=annotations, description=desc)

    # pylint: disable=too-many-return-statements
    def __parse_tag(self, name, desc):
        if name.lower() == "since":
            return self.__parse_since_tag(name, desc)
        elif name.lower() == "returns":
            return self.__parse_returns_tag(name, desc)
        elif name.lower() == "return value":
            return self.__parse_returns_tag("returns", desc)
        elif name.lower() == "stability":
            return self.__parse_stability_tag("stability", desc)
        elif name.lower() == "deprecated":
            return self.__parse_deprecated_tag("deprecated", desc)
        else:
            validator = self.doc_tool.tag_validators.get(name)
            if not validator:
                print "FIXME no tag validator"
                return None
            if not validator.validate(desc):
                print "invalid value for tag %s : %s" % name, desc
                return None
            return Tag(name=name, description=desc)

    def __parse_description_and_tags(self, desc_and_tags):
        dts = self.tag_validation_regex.split(desc_and_tags)
        tags = []

        desc = dts[0]
        if len(dts) == 1:
            return desc, tags

        # pylint: disable=unused-variable
        for raw, name, tag_desc in _grouper(dts[1:], 3):
            tag = self.__parse_tag(name.strip(), tag_desc.strip())
            if tag:
                tags.append(tag)

        return desc, tags

    def __strip_comment(self, comment):
        comment = re.sub(r'^[\W]*\/[\*]+[\W]*', '', comment)
        comment = re.sub(r'\*\/[\W]*$', '', comment)
        comment = re.sub(r'\n[ \t]*\*', '\n', comment)
        return comment.strip()

    def __validate_c_comment(self, comment):
        return re.match(r'(/\*\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)$',
                        comment) is not None

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    def parse_comment(self, comment, filename, lineno, endlineno,
                      include_paths, stripped=False):
        """
        Returns a Comment given a string
        """
        if not stripped and not comment.lstrip().startswith('/**'):
            return None

        if not self.__validate_c_comment(comment.strip()):
            return None

        raw_comment = comment
        if not stripped:
            comment = self.__strip_comment(comment)

        comment = add_md_includes(unicode(comment.decode('utf8')),
                                  filename, include_paths, lineno)

        split = re.split(r'\n[\W]*\n', comment, maxsplit=1)
        block_name, parameters, annotations = \
            self.__parse_title_and_parameters(split[0])

        if not block_name:
            return None

        description = ""
        tags = []
        if len(split) > 1:
            description, tags = self.__parse_description_and_tags(split[1])

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

        block = Comment(name=block_name, filename=filename, lineno=lineno,
                        endlineno=endlineno,
                        annotations=annotations, params=actual_parameters,
                        description=description,
                        short_description=short_description,
                        title=title, tags=tags, raw_comment=raw_comment)

        return block
