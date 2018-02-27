import sys
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import datetime


Base = declarative_base()

class GoogleUser(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key=True)
	name = Column(String(250), nullable=False)
	email = Column(String(250), nullable=False)
	picture = Column(String(250))

class Category(Base):
	__tablename__ = 'category'

	id = Column(Integer, primary_key = True)
	name = Column(String(80), nullable = False)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(GoogleUser)

	@property
	def serialize(self):
	    """Return object data in easily serializeable format"""
	    return {
	    	'id': self.id,
	        'name': self.name,
	    }

class CategoryItem(Base):
	__tablename__ = 'category_item'

	name = Column(String(80), nullable = False)
	description = Column(String(250))
	id = Column(Integer, primary_key = True)
	category_id = Column(Integer, ForeignKey('category.id'))
	category = relationship(Category)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(GoogleUser)

	@property
	def serialize(self):
	    """Return object data in easily serializeable format"""
	    return {
	        'category': self.category.name,
	        'description': self.description,
	        'name': self.name,
	    }

class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String)
    createdDate = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(GoogleUser)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'description': self.description,
            'user_id': self.user_id
        }


engine = create_engine('sqlite:///catalog_database.db')
Base.metadata.create_all(engine)