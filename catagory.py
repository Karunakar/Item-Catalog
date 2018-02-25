from flask import url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, User, Category, Item
import sqlite3


conn = sqlite3.connect('test.db')
print "Opened database successfully";

engine = create_engine('sqlite:///catelog1.db')
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

item1 = Item(user_id=1, name="Cate Gory",
                     description="The Carina Nebula (also known as the Great Nebula in Carina, the Eta Carinae Nebula, NGC 3372, as well as the Grand Nebula) is a large complex area of bright and dark nebulosity in the constellation of Carina, and is located in the CarinaSagittarius Arm. The nebula lies at an estimated distance between 6,500 and 10,000 light years from Earth. The nebula is one of the largest diffuse nebulae in our skies. Although it is some four times as large and even brighter than the famous Orion Nebula, the Carina Nebula is much less well known, due to its location in the southern sky. It was discovered by Nicolas Louis de Lacaille in 1751 from the Cape of Good Hope. Source: Wikipedia.com",
                     category=category1)
session.add(item1)
session.commit()

