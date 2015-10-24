import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, PickleType
from hotdoc.core.alchemy_integration import Base, engine

class CommentBlock(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    title = Column(String)
    params = Column(PickleType)
    filename = Column(String, default='')
    lineno = Column(Integer)
    annotations = Column(PickleType, default={})
    params = Column(PickleType, default={})
    description = Column(String)
    short_description = Column(String)
    tags = Column(PickleType, default={})

    def add_param_block (self, param_name, block):
        self.params[param_name] = block

    def set_return_block (self, block):
        self.tags['returns'] = block

    def set_description (self, description):
        self.description = description.strip();

class GtkDocAnnotation(Base):
    __tablename__ = 'annotations'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    argument = Column(PickleType)

class GtkDocTag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(String)
    annotations = Column(PickleType, default={})
    description = Column(String)

class GtkDocParameter(CommentBlock):
    pass

Base.metadata.create_all(engine)
