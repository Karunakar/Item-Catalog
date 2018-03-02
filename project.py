from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
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
from categories_menu_setup import Base, GoogleUser, Category, Item

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Items Application"


engine = create_engine('sqlite:///catalog_database.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/logout')
def logout():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
          gdisconnect()
          del login_session['gplus_id']
          del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['user_id']
        del login_session['provider']
        flash("you have succesfully been logout")
        print login_session['username']
        return redirect(url_for('login'))
    else:
        flash("you were not logged in")
        return redirect(url_for('showHome'))
	
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

def createUser(login_session):
    newUser = GoogleUser(name=login_session['username'], email=login_session['email'])
    session.add(newUser)
    session.commit()
    user = session.query(GoogleUser).filter_by(email=login_session['email']).one()
    return user.id

@app.route('/categories.json')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(Categories = [c.serialize for c in categories])

def getUserInfo(user_id):
    user = session.query(GoogleUser).filter_by(id=user_id).one()
    return user

@app.route('/')
def rootPage():
    items = session.query(Item)
    categories = session.query(Category)
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
       for x in xrange(32))
    login_session['state'] = state
    return render_template('root.html', STATE=state, categories=categories, items=items)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('showLogin', next=request.url))
    return decorated_function
	
@app.route('/catalog/<name>/items')
def showItems(name):
    cat_list = session.query(Category)
    Cat = session.query(Category).filter_by(name=name).one()
    items = session.query(Item).filter_by(category_id=Cat.id)
    creator = getUserInfo(Cat.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('withoutLoginCategoryItems.html', categories=cat_list, chosenCategory=Cat, items=items)
    else:
        return render_template('loginCategoryItems.html', categories=cat_list, chosenCategory=Cat, items=items)	

	
@app.route('/catalog/categorynew', methods=['GET','POST'])
@login_required
def CategoryNew():
    if request.method == 'POST':
        addingCategory = Category(name=request.form['name'], user_id=login_session['user_id'])
        session.add(addingCategory)
        session.commit()
        return redirect(url_for('showHome'))
    else:
        return render_template('categoryNew.html')


@app.route('/catalog')
def showHome():
    categories = session.query(Category)
    items = session.query(Item)
    if 'username' not in login_session:
        return render_template('homewithoutlogin.html', categories=categories, items=items)
    else:
        return render_template('root.html', categories=categories, items=items)
		
		
		
@app.route('/catalog/newitem', methods=['GET','POST'])
@login_required
def newItem():
    categories = session.query(Category)
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
            return render_template('itemNew.html', categories=categories)
    else:
        return render_template('itemNew.html', categories=categories)
		
@app.route('/catalog/<c_name>/edit', methods=['GET','POST'])
@login_required
def CategoryEdit(c_name):
    cat = session.query(Category).filter_by(name=c_name).one()
    if request.method == 'POST':
        cat.name = request.form['name']
        session.add(cat)
        session.commit()
        return redirect(url_for('showHome'))
    else:
        return render_template('categoryEdit.html', category=cat)
	
@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID doesn't match app's"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt':'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    login_session['username'] = data['name']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
   
    flash("You Are Now Logged In As %s" % login_session['username'])
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
 

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/catalog/<c_name>/<i_name>')
def showItem(c_name, i_name):
    categories = session.query(Category)
    chosenCategory = session.query(Category).filter_by(name=c_name).one()
    items = session.query(Item).filter_by(category_id=chosenCategory.id)
    cat = session.query(Category).filter_by(name=c_name).one()
    item = session.query(Item).filter_by(name=i_name, category=cat).one()
    creator = getUserInfo(item.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('withoutloginitems.html', item=item)
    else:
        return render_template('itemShow.html', item=item, creator=creator,categories=categories, items=items)



@app.route('/catalog/<c_name>/<i_name>/edit', methods=['GET','POST'])
@login_required
def editItem(c_name, i_name):
    categories = session.query(Category)
    editingItemCategory = session.query(Category).filter_by(name=c_name).one()
    editingItem = session.query(Item).filter_by(name=i_name, category=editingItemCategory).one()
    if request.method == 'POST':
		editingItem.name = request.form['name']
		editingItem.description = request.form['description']
		editingItem.category = session.query(Category).filter_by(name=request.form['category']).one()
		session.add(editingItem)
		session.commit()
		return redirect(url_for('showItem', c_name=editingItemCategory.name, i_name=editingItem.name))
    else:
        return render_template('editItem.html', categories=categories, editingItemCategory=editingItemCategory, item=editingItem)

@app.route('/catalog/<c_name>/<i_name>/delete', methods=['GET','POST'])
@login_required
def ItemDelete(c_name, i_name):
    category = session.query(Category).filter_by(name=c_name).one()
    deletingItem = session.query(Item).filter_by(name=i_name, category=category).one()
    if request.method == 'POST':
        session.delete(deletingItem)
        session.commit()
        return redirect(url_for('showItems', name=category.name))
    else:
        return render_template('itemDelete.html', item=deletingItem)
		
		
if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
