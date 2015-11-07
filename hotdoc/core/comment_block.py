import os
import linecache

class CommentBlock(object):
    def __init__(self, name='', title='', params={}, filename='',
            lineno=-1, annotations={}, description='', short_description='',
            tags={}, raw_comment=''):
        self.name = name
        self.title = title
        self.params = params
        self.filename = os.path.abspath(filename)
        self.lineno = lineno
        self.annotations = annotations
        self.description = description
        self.short_description = short_description
        self.tags = tags

        leading_ws = ''
        if lineno != -1:
            orig = linecache.getline(filename, lineno)
            leading_ws = (len(orig) - len (orig.lstrip(' '))) * ' '

        self.raw_comment = leading_ws + raw_comment

    def add_param_block (self, param_name, block):
        self.params[param_name] = block

    def set_return_block (self, block):
        self.tags['returns'] = block

    def set_description (self, description):
        self.description = description.strip();

class GtkDocAnnotation(object):
    def __init__(self, name, argument=None):
        self.name = name
        self.argument = argument

class GtkDocTag(object):
    def __init__(self, name, description, value=None, annotations={}):
        self.name = name
        self.description = description
        self.annotations = annotations

class GtkDocParameter(CommentBlock):
    pass

def comment_from_tag(tag):
    if not tag:
        return None
    comment = CommentBlock (name=tag.name,
            description=tag.description,
            annotations=tag.annotations)
    return comment
