from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
from flask import session as login_session
import random
from sqlalchemy import desc
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from functools import wraps


import os

from database_setup import Base, User, Category, Item

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Items Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///catalog_database.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)
	
	
@app.route('/logout')
def logout():
    print login_session['username']
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
          gdisconnect()
          del login_session['gplus_id']
          del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("you have succesfully been logout")
        print login_session['username']
        return redirect(url_for('login'))
    else:
        flash("you were not logged in")
        return redirect(url_for('showRestaurants'))



# API endpoints for all categories.
@app.route('/categories.json')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(Categories = [c.serialize for c in categories])



# Show cover page
@app.route('/')
def rootPage():
    items = session.query(Item).order_by(desc(Item.createdDate))
    categories = session.query(Category).order_by(asc(Category.name))
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
       for x in xrange(32))
    login_session['state'] = state
    return render_template('root.html', STATE=state, categories=categories, items=items)

# Check for user login status
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('showLogin', next=request.url))
    return decorated_function
	
	


# Show home page
@app.route('/catalog')
def showHome():
    categories = session.query(Category).order_by(asc(Category.name))
    items = session.query(Item).order_by(desc(Item.createdDate))
    if 'username' not in login_session:
        return render_template('publichome.html', categories=categories, items=items)
    else:
        return render_template('root.html', categories=categories, items=items)



	
# Connect user using Google Plus account.
@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        """Upgrade the authorization code into a credentials object"""
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    """Check that access token is valid"""
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    """If there was an error in the access token info, abort"""
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    """Verify that the access token is used for the intended user"""
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    """Verify that the access token is valid for this app"""
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID doesn't match app's"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    """Check to see if user is already logged in"""
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    """Store the access token in the session for later use"""
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    """Get user info and store in login session for later use"""
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt':'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    """See if user exists, if it doesn't make a new one"""
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    """Render welcome message if user logged in successfully"""
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("You Are Now Logged In As %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    # print login_session['username']

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print login_session['access_token']
    print result


    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response



	
# Show all items in a category
@app.route('/catalog/<category_name>/items')
def showCategoryItems(category_name):
    categories = session.query(Category).order_by(asc(Category.name))
    chosenCategory = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(category_id=chosenCategory.id).order_by(asc(Item.name))
    creator = getUserInfo(chosenCategory.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('withoutLoginCategoryItems.html', categories=categories, chosenCategory=chosenCategory, items=items)
    else:
        return render_template('loginCategoryItems.html', categories=categories, chosenCategory=chosenCategory, items=items)	

# Add a new category
@app.route('/catalog/newcategory', methods=['GET','POST'])
@login_required
def newCategory():
    if request.method == 'POST':
        addingCategory = Category(name=request.form['name'], user_id=login_session['user_id'])
        session.add(addingCategory)
        session.commit()
        return redirect(url_for('showHome'))
    else:
        return render_template('newCategory.html')
	
# Add a new item
@app.route('/catalog/newitem', methods=['GET','POST'])
@login_required
def newItem():
    categories = session.query(Category).order_by(asc(Category.name))
    if request.method == 'POST':
        itemName = request.form['name']
        itemDescription = request.form['description']
        itemCategory = session.query(Category).filter_by(name=request.form['category']).one()
        if itemName != '':
            print "item name %s" % itemName
            addingItem = Item(name=itemName, description=itemDescription,  category=itemCategory,
                              user_id=itemCategory.user_id)
            session.add(addingItem)
            session.commit()
            return redirect(url_for('showHome'))
        else:
            return render_template('newItem.html', categories=categories)
    else:
        return render_template('newItem.html', categories=categories)

	


# Edit a category
@app.route('/catalog/<category_name>/edit', methods=['GET','POST'])
@login_required
def editCategory(category_name):
    categoryToEdit = session.query(Category).filter_by(name=category_name).one()

    """Prevent logged-in user to edit other user's category"""
    if categoryToEdit.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this category. Please create your own " \
               "category " \
               "in order to edit.');}</script><body onload='myFunction()'>"

    """Save edited category to the database"""
    if request.method == 'POST':
        categoryToEdit.name = request.form['name']
        session.add(categoryToEdit)
        session.commit()
        return redirect(url_for('showHome'))
    else:
        return render_template('editCategory.html', category=categoryToEdit)




# Show information of a specific item
@app.route('/catalog/<category_name>/<item_name>')
def showItem(category_name, item_name):
    categories = session.query(Category).order_by(asc(Category.name))
    chosenCategory = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(category_id=chosenCategory.id).order_by(asc(Item.name))
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(Item).filter_by(name=item_name, category=category).one()
    creator = getUserInfo(item.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('withoutloginitems.html', item=item)
    else:
        return render_template('showItem.html', item=item, creator=creator,categories=categories, items=items)



# Edit an item
@app.route('/catalog/<category_name>/<item_name>/edit', methods=['GET','POST'])
@login_required
def editItem(category_name, item_name):
    categories = session.query(Category).order_by(asc(Category.name))
    editingItemCategory = session.query(Category).filter_by(name=category_name).one()
    editingItem = session.query(Item).filter_by(name=item_name, category=editingItemCategory).one()

    """Prevent logged-in user to edit item which belongs to other user"""
    if editingItem.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this item. Please create your own item " \
               "in order to edit.');}</script><body onload='myFunction()'>"

    """Save edited item to the database"""
    if request.method == 'POST':
        if request.form['name']:
            editingItem.name = request.form['name']
        if request.form['description']:
            editingItem.description = request.form['description']
        if request.form['category']:
            editingItem.category = session.query(Category).filter_by(name=request.form['category']).one()
        session.add(editingItem)
        session.commit()
        return redirect(url_for('showItem', category_name=editingItemCategory.name, item_name=editingItem.name))
    else:
        return render_template('editItem.html', categories=categories, editingItemCategory=editingItemCategory, item=editingItem)

# Delete an item
@app.route('/catalog/<category_name>/<item_name>/delete', methods=['GET','POST'])
@login_required
def deleteItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    deletingItem = session.query(Item).filter_by(name=item_name, category=category).one()

    """Prevent logged-in user to delete item which belongs to other user"""
    if deletingItem.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this item. Please create your own item " \
               "in order to delete.');}</script><body onload='myFunction()'>"

    """Delete item from the database"""
    if request.method == 'POST':
        session.delete(deletingItem)
        session.commit()
        return redirect(url_for('showCategoryItems', category_name=category.name))
    else:
        return render_template('deleteItem.html', item=deletingItem)
		
		
if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
