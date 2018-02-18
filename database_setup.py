from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import datetime

Base = declarative_base()


class Restaurant(Base):
    __tablename__ = 'restaurant'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }


class MenuItem(Base):
    __tablename__ = 'menu_item'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    price = Column(String(8))
    course = Column(String(250))
    restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
    restaurant = relationship(Restaurant)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'price': self.price,
            'course': self.course,
        }



class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,

        }

class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    items = relationship("Item", cascade="all, delete-orphan")

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'user_id': self.user_id
        }

class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String)
    image = Column(String)
    createdDate = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'description': self.description,
            'user_id': self.user_id
        }


engine = create_engine('sqlite:///catelog.db')


Base.metadata.create_all(engine)


Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)

session = DBSession()

# Create dummy user
user1 = User(name="Tyler Huynh", email="tylerhuynh100@gmail.com", picture="https://cdn2.iconfinder.com/data/icons/happy-users/100/users09-512.png")
session.add(user1)
session.commit()

# Create category #1 and add items to the category
category1 = Category(name="Diffuse Nebulae", user_id=1)
session.add(category1)
session.commit()

item1 = Item(user_id=1, name="Carina Nebula",
                     description="The Carina Nebula (also known as the Great Nebula in Carina, the Eta Carinae Nebula, NGC 3372, as well as the Grand Nebula) is a large complex area of bright and dark nebulosity in the constellation of Carina, and is located in the CarinaSagittarius Arm. The nebula lies at an estimated distance between 6,500 and 10,000 light years from Earth. The nebula is one of the largest diffuse nebulae in our skies. Although it is some four times as large and even brighter than the famous Orion Nebula, the Carina Nebula is much less well known, due to its location in the southern sky. It was discovered by Nicolas Louis de Lacaille in 1751 from the Cape of Good Hope. Source: Wikipedia.com",
                     image = "/static/carina_nebula.jpg",
                     category=category1)
session.add(item1)
session.commit()


