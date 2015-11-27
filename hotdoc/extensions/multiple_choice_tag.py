from hotdoc.core.base_extension import BaseExtension
from hotdoc.core.comment_block import TagValidator

MULTIPLE_CHOICE_DESCRIPTION=\
"""
Add a multiple choice tag for consumption by comment parsers.

Syntax: tagname:possible,values:default
Example : my_tag:foo,bar,baz:foo

You can omit possible values and default, for example these
are valid syntaxes:

>>> ['my_tag::foo']
>>> ['my_tag:foo,bar,baz:']
>>> ['my_tag::']

Default tags will be set on every symbol in the library.
"""

class MultipleChoiceTagValidator(TagValidator):
    def __init__(self, name, choices=None, default=None):
        TagValidator.__init__(self, name)
        self.choices = choices
        self.default = default

    def validate(self, value):
        if not self.choices:
            return True

        return value in self.choices

DESCRIPTION=\
"""
This extension allows to add custom tags to the
tags recognized by the comment parsers.

For now, it supports creating new multiple choice tags.
"""

def validator_from_prototype(prototype):
    split = prototype.split(':')
    if len (split) != 3:
        print "Invalid syntax for multiple choice tag %s" % prototype
        return None

    name = split[0]
    if not name:
        print "Invalid prototype, missing name : %s" % prototype
        return None

    choices = [choice for choice in split[1].split(',') if choice]

    default = split[2]

    if default and choices and default not in choices:
        print "Invalid prototype %s, default %s is not part of %s" % \
                (prototype, default, choices)
        return None

    return MultipleChoiceTagValidator(name, choices, default)

def validate_prototypes(wizard, prototypes):
    if not wizard.validate_list(wizard, prototypes):
        return False

    for prototype in prototypes:
        if not isinstance (prototype, basestring):
            print 'This is not a string : %s' % prototype
            return False

        if validator_from_prototype(prototype) is None:
            return False

    return True

class TagExtension(BaseExtension):
    EXTENSION_NAME='core-tags'

    def __init__(self, doc_tool, args):
        BaseExtension.__init__(self, doc_tool, args)
        tag_prototypes = args.get('tag_prototypes', [])
        for prototype in tag_prototypes:
            validator = validator_from_prototype(prototype)
            if validator:
                self.info ("Registering multiple choice tag %s with choices %s and default %s"
                        % (validator.name, validator.choices, validator.default))
            doc_tool.register_tag_validator(validator)

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('core tags customization',
                DESCRIPTION)
        group.add_argument('--multiple-choice-tags', action="store",
                extra_prompt=MULTIPLE_CHOICE_DESCRIPTION,
                help="Define multiple choice tags",
                nargs='+', dest='tag_prototypes',
                validate_function=validate_prototypes)
