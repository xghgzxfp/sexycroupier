# coding: utf-8

from datetime import datetime, timedelta
from flask import Flask, session, flash, render_template, request, redirect, url_for
from pymongo import MongoClient
from . import config


app = Flask(__name__)
app.config.from_object(config)
db = app.db = MongoClient(app.config['MONGO_URI'])[app.config['MONGO_DBNAME']]

from . import model

title = "2018 World Cup"


def redirect_url():
    return request.args.get('next') or \
        request.referrer or \
        url_for('index')


@app.route("/")
@app.route("/login", methods=['GET', 'POST'])
def login():
        # Display the login screen
    error = None
    if request.method == 'GET':
        if session.get('logged_in'):
            return redirect(url_for('index'))
        return render_template('login.html', t=title, error=error)
    else:
        name = request.values.get("username")
        pw = request.values.get("password")
        if db.users.find({"username": name}).limit(1).count() == 0:
            error = "user doesn't exist"
        elif db.users.find({"username": name}, {"password": 1})[0]["password"] != pw:
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


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'GET':
        return render_template('register.html', t=title, h="Create your account", error=error)
    else:
        name = request.values.get("username")
        pw = request.values.get("password")
        pw1 = request.values.get("password2")

        if db.users.find({"username": name}).limit(1).count() == 1:
            error = "your username is already registered"
        elif pw != pw1:
            error = "password input not same"
        else:
            db.users.insert({"username": name, "password": pw})
            flash("Your account has been set up sucessfully")
            return redirect("/login")
        return render_template('register.html', t=title, error=error)


@app.route('/index')
def index():
    if not session.get('logged_in'):
        flash('please login')
        return redirect("/login")
    # print( session['logged_user'])

    userteams = db.auction.find({"owner": session['logged_user']})
    today = datetime.now()
    dayaftertomorrow = today + timedelta(days=2)

    games = db.match.find({"$and": [{"match_time": {"$gte": today}},
                             {"match_time": {"$lt": dayaftertomorrow}}]})

    return render_template('index.html', username=session['logged_user'], userteams=userteams, games=list(games))


@app.route('/bet', methods=['POST'])
def bet():

    match_id = request.values.get("match_id")
    new_choice = request.values.get("betchoice")
    print(request.values)

    ## function place holder:
    ## check if current time is an effective time point to modify the bet choice

    model.update_match_gamblers(match_id, new_choice, session["logged_user"])
    redir = redirect_url()
    return redirect(redir)


if __name__ == "__main__":
    app.run(port=8010)
