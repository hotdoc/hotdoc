import sqlalchemy
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, mapper
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

engine = create_engine('sqlite:///hotdoc.db')
Session = sessionmaker(bind=engine)
session = Session()

@event.listens_for(mapper, 'init')
def auto_add (target, args, kwargs):
    session.add(target)
    session.flush()
