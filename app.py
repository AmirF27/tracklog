import os
import unirest
import urllib2
import urllib

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, current_user
from sqlalchemy import func
from passlib.apps import custom_app_context as pwd_context
from models import *
from database import db_session
from helpers import *
from flask_jsglue import JSGlue

app = Flask(__name__)
app.secret_key = 'some_secret'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"

JSGlue(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not all([username, password]):
            flash("Username and/or password missing.")
            return render_template("login.html")

        user = db_session.query(User).filter(func.lower(User.username) == func.lower(username)).first()

        if not user:
            flash("The username you've entered does not exist")
            return render_template("login.html")

        if not pwd_context.verify(password, user.password):
            flash("You've entered a wrong password!")
            return render_template("login.html")

        if request.form.get("remember"):
            remember = True
        else:
            remember = False

        # https://flask-login.readthedocs.io/en/latest/
        login_user(user, remember=remember)

        next = request.args.get("next")

        if not is_safe_url(next):
            return abort(400)

        return redirect(next or url_for("index"))
    else:
        return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if not all([username, email, password, confirm]):
            return render_template("register.html")

        if password != confirm:
            return render_template("register.html")

        user = User(username, email, pwd_context.encrypt(password))

        db_session.add(user)
        db_session.commit();

        login_user(user, remember=False)

        return redirect(url_for("index"))
    else:
        return render_template("register.html")

@app.route("/backlog")
@login_required
def backlog():

    backlog = db_session.query(ListEntry).filter(ListEntry.user_id == current_user.id)
    platforms = db_session.query(Platform.name).join(UserPlatform).filter(UserPlatform.user_id == current_user.id)

    return render_template("backlog.html", entries=backlog, platforms=platforms)

@app.route("/search")
def search():

    q = request.args.get("q")

    if not q:
        raise RuntimeError("missing parameter: q")

    api_key = os.environ.get("API_KEY")

    if not api_key:
        raise RuntimeError("API_KEY not set")

    # http://unirest.io/python.html
    response = unirest.get("https://igdbcom-internet-game-database-v1.p.mashape.com/games/",
        headers={ 
            "X-Mashape-Key": api_key,
            "Accept": "application/json"
        }, 
        params={ 
            "fields": "name,cover",
            "limit": 10,
            "search": q
        }
    ).body

    return jsonify(response)

@app.route("/platforms")
def platforms():

    id = request.args.get("id")

    if not id:
        raise RuntimeError("missing parameter: id")

    key = os.environ.get("API_KEY")

    if not key:
        raise RuntimeError("API_KEY not set")

    response = unirest.get("https://igdbcom-internet-game-database-v1.p.mashape.com/games/{}?fields=release_dates.platform".format(id),
        headers={
            "X-Mashape-Key": key,
            "Accept": "application/json"
        }
    )

    # platforms = [];

    # for release_date in response.body[0].get("release_dates"):
    #     platform = unirest.get("https://igdbcom-internet-game-database-v1.p.mashape.com/platforms/{}?fields=name".format(release_date.get("platform")),
    #         headers={
    #             "X-Mashape-Key": key,
    #             "Accept": "application/json"
    #         }
    #     )
    #     platforms.append(platform.body[0].get("name"));

    platforms = unirest.get("https://igdbcom-internet-game-database-v1.p.mashape.com/platforms/?fields=name&limit=100",
        headers={
            "X-Mashape-Key": key,
            "Accept": "application/json"
        }
    )

    return jsonify(platforms.body)

@login_manager.user_loader
def load_user(user_id):
    """
    https://flask-login.readthedocs.io/en/latest/
    """

    return User.query.get(user_id)

if __name__ == "__main__":
    app.run()
