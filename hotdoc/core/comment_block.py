import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, PickleType
from sqlalchemy.sql import exists
from hotdoc.core.alchemy_integration import Base, engine, session


class CommentBlock(object):
    def __init__(self, name='', title='', params={}, filename='',
            lineno=-1, annotations={}, description='', short_description='',
            tags={}):
        self.name = name
        self.title = title
        self.params = params
        self.filename = filename
        self.lineno = lineno
        self.annotations = annotations
        self.description = description
        self.short_description = short_description
        self.tags = tags

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

Base.metadata.create_all(engine)
