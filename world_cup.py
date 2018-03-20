#!/usr/local/bin/python3
# coding=utf-8

from flask import Flask, session, flash, render_template,request,redirect,url_for # For flask implementation
from pymongo import MongoClient # Database connector


client = MongoClient('localhost', 27017)    #Configure the connection to the database
db = client.worldcup    #Select the database
users = db.user #Select the collection of user login

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'super secret key'
title = "2018 World Cup"

@app.route("/")
@app.route("/login", methods = ['GET' , 'POST'])
def login():
	#Display the login screen
    error = None
    if request.method == 'GET':
        if session.get('logged_in') != None:
            return redirect(url_for('index'))
        return render_template('login.html', t=title, error=error)
    else:
        name = request.values.get("username")
        pw = request.values.get("password")
        if users.find({"username": name}).limit(1).count() == 0:
            error = "user doesn't exist"
        elif users.find( { "username": name }, { "password": 1 } )[0]["password"] != pw:
            error = "incorrect password"
        else:
            session["logged_in"] = True
            session["logged_user"] = name
            flash("You were sucessfully logged in!")
            return redirect(url_for('index'))
        return render_template('login.html', t=title, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('logged_user', None)
    flash('You were logged out')
    return redirect(url_for('login'))

@app.route('/register' , methods = ['GET' , 'POST'])
def register():
    error = None
    if request.method == 'GET':
        return render_template('register.html', t=title, h="Create your account", error=error)
    else:
        name = request.values.get("username")
        pw = request.values.get("password")
        pw1 = request.values.get("password2")

        if users.find({"username": name}).limit(1).count() == 1:
            error = "your username is already registered"
        elif pw != pw1:
            error = "password input not same"
        else:
            users.insert({"username": name, "password": pw})
            flash("Your account has been set up sucessfully")
            return redirect("/login")
        return render_template('register.html', t=title, error=error)

@app.route('/index')
def index():
    if session.get('logged_in') == None:
        flash('please login')
        return redirect("/login")
    print( session['logged_user'])

    return render_template('index.html', username = session['logged_user'], userteams = db.auction.find({"owner" : session['logged_user']}))

if __name__ == "__main__":
    app.run(debug=True)
# Careful with the debug mode..



