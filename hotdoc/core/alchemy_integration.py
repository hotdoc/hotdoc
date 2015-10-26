import sqlalchemy
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, mapper
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable

Base = declarative_base()

engine = create_engine('sqlite:///hotdoc.db')
Session = sessionmaker(bind=engine)
session = Session()
session.autoflush = False

class MutableDict(Mutable, dict):

    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)
            return Mutable.coerce(key, value)
        else:
            return value

    def __delitem(self, key):
        dict.__delitem__(self, key)
        self.changed()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(self)

class MutableObject(Mutable, object):
    @classmethod
    def coerce(cls, key, value):
        return value

    def __getstate__(self): 
        d = self.__dict__.copy()
        d.pop('_parents', None)
        return d

    def __setstate__(self, state):
        self.__dict__ = state

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        self.changed()

@event.listens_for(mapper, 'init')
def auto_add (target, args, kwargs):
    session.add (target)

def purge_db():
    session.flush()

def finalize_db ():
    pass
