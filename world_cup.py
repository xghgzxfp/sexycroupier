#!/usr/local/bin/python3
# coding=utf-8

from flask import Flask, render_template,request,redirect,url_for # For flask implementation
from pymongo import MongoClient # Database connector


client = MongoClient('localhost', 27017)    #Configure the connection to the database
db = client.worldcup    #Select the database
users = db.user #Select the collection of user login

app = Flask(__name__)
title = "2018 World Cup"

@app.route("/")
@app.route("/login")
def login():
	#Display the login screen
	return render_template('login.html', t=title, h="Login")

@app.route('/register' , methods = ['GET' , 'POST'])
def register():
	if request.method == 'POST':
		name = request.values.get("username")
		pw = request.values.get("passwd")
		pw1 = request.values.get("passwd2")

		if users.find({"username": name}).limit(1).count() == 1:
			return ("your username is already registered")

		if pw != pw1:
			return ("password input not same")

		users.insert({"username": name, "password": pw})

		return redirect("/login")
	else:
		return render_template('register.html', t=title, h="Create your account")


if __name__ == "__main__":
	app.run(debug=True)
# Careful with the debug mode..



