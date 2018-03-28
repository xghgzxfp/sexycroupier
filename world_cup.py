# coding: utf-8

from datetime import datetime, timedelta
from flask import Flask, session, flash, render_template, request, redirect, url_for
from pymongo import MongoClient


client = MongoClient('localhost', 27017)
db = client.worldcup
users = db.user

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'super secret key'
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
        if users.find({"username": name}).limit(1).count() == 0:
            error = "user doesn't exist"
        elif users.find({"username": name}, {"password": 1})[0]["password"] != pw:
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
    if not session.get('logged_in'):
        flash('please login')
        return redirect("/login")
    # print( session['logged_user'])

    userteams = db.auction.find({"owner": session['logged_user']})
    today = datetime(2016, 6, 11, 0, 0)
    dayaftertomorrow = today + timedelta(days=2)

    games = db.schedule.aggregate([
        {"$match": {"$and": [{"date": {"$gte": today}},
                             {"date": {"$lt": dayaftertomorrow}}]}},
        {"$sort": {"date": 1}},
        {"$lookup": {
            "localField": "id",
            "from": "betinfo",
            "foreignField": "match_id",
            "as": "binfo"
        }},
        {"$unwind": "$binfo"},
        {"$match": {"binfo.player_id": session["logged_user"]}},
        {"$sort": {"binfo.ctime": -1}},
        {"$limit": 1},
        {"$project": {
            "id": 1,
            "date": 1,
            "a.team": 1,
            "a.handicap": 1,
            "b.team": 1,
            "b.handicap": 1,
            "binfo.team": 1,
            "_id": 0
        }}
    ])

    return render_template('index.html', username=session['logged_user'], userteams=userteams, games=list(games))


@app.route('/betupdate', methods=['GET', 'POST'])
def betupdate():

    match_id = request.values.get("matchid")
    new_choice = request.values.get("choice")
    print(request.values)

    db.betinfo.insert({
        "match_id": match_id,
        "player_id": session["logged_user"],
        "team": db.schedule.find_one({"id": match_id})[new_choice]["team"],
        "ctime": datetime.now()
    })

    redir = redirect_url()

    return redirect(redir)


if __name__ == "__main__":
    app.run(port=8010)
