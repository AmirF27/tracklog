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
    """
    Route for user login
    """
    
    # if the route was reached via a POST request (user tried to log in)
    if request.method == "POST":
        # retrieve username and password from submitted form
        username = request.form.get("username")
        password = request.form.get("password")

        # make sure username and password fields weren't blank
        if not all([username, password]):
            flash("Username and/or password missing.")
            return render_template("login.html")

        # query database for user
        user = db_session.query(User).filter(func.lower(User.username) == func.lower(username)).first()

        # check if the user exists
        if not user:
            flash("The username you've entered does not exist.")
            return render_template("login.html")

        # check if the entered password is correct
        if not pwd_context.verify(password, user.password):
            flash("You've entered a wrong password!")
            return render_template("login.html")

        # determine whether to remember user or not
        if request.form.get("remember"):
            remember = True
        else:
            remember = False

        # all went well, login user
        # https://flask-login.readthedocs.io/en/latest/
        login_user(user, remember=remember)

        # determine the last page the user was on
        next = request.args.get("next")

        if not is_safe_url(next):
            return abort(400)

        # redirect user to the last page they were on
        # or to index otherwise
        return redirect(next or url_for("index"))
    # if the route was reached via a GET request
    else:
        return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    """
    Route for user logout
    """

    logout_user()

    return redirect(url_for("index"))

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Route for user registration
    """

    # if the route was reached via a POST request (user tried to register)
    if request.method == "POST":
        # retrieve form data
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        # make sure none of the fields in the form were blank
        if not all([username, email, password, confirm]):
            flash("Username, email, password, and/or password confirmation missing. \
                Please fill in all of the fields and try again.")
            return render_template("register.html")

        # make sure password and password confirmation match
        if password != confirm:
            flash("Password and password confirmation did not match.")
            return render_template("register.html")

        # create a user object, and encrypt their password
        user = User(username, email, pwd_context.encrypt(password))

        # insert the user into the database
        db_session.add(user)
        db_session.commit();

        # log the user in for convenience
        login_user(user, remember=False)

        return redirect(url_for("index"))
    # if the route was reached via a GET request
    else:
        return render_template("register.html")

@app.route("/backlog", methods=["GET", "POST"])
@login_required
def backlog():
    """
    Route for displaying user backlog
    TODO: move game adding functionality to separate route
    """

    if request.method == "POST":
        # retrieve form data
        platform = request.form.get("platform")
        igdb_id = request.form.get("igdb_id")
        game = request.form.get("game_name")
        image_url = request.form.get("image_url")

        # make sure none of the fields in the form were blank
        if not all([platform, igdb_id, game, image_url]) or platform == "Platform":
            flash("Game and/or platform missing, couldn't add to backlog. Please try again.", "danger")
            return redirect(url_for("backlog"))

        # get platform ID from database based on the value provided in the form
        platform_id = db_session.query(Platform.id).filter(Platform.name == platform).one().id

        # query the database and check if the entry the user is about to add
        # already exists, in order to ensure the user doesn't add duplicates
        if not db_session.query(ListEntry).filter(ListEntry.user_id == current_user.id). \
                                           filter(ListEntry.game == game). \
                                           filter(ListEntry.platform_id == platform_id):
            # if the entry doesn't exist in the database, insert it
            db_session.add(ListEntry(current_user.id, platform_id, igdb_id, game, image_url, "backlog"))
            db_session.commit()
        # if the entry is already in the database
        else:
            flash("{} is already in your backlog under {}.".format(game, platform), "danger")
            return redirect(url_for("backlog"))

        flash("{} successfully added to your backlog under {}.".format(game, platform), "success")
        return redirect(url_for("backlog"))
    else:
        backlog = db_session.query(ListEntry).filter(ListEntry.user_id == current_user.id).order_by(ListEntry.game)
        platforms = db_session.query(Platform.name).join(UserPlatform).filter(UserPlatform.user_id == current_user.id)

        return render_template("backlog.html", entries=backlog, platforms=platforms)

@app.route("/search")
def search():
    """
    Route for searching IGDB's API for games as the user types
    IGDB: https://www.igdb.com/
    """

    # retrieve search query from request and make sure it's not missing
    q = request.args.get("q")
    if not q:
        raise RuntimeError("missing parameter: q")

    # retrieve the API key from the environment variables and make sure it's not missing
    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY not set")

    # search API for matching games
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

    # return the search results
    return jsonify(response)

@app.route("/delete", methods=["POST"])
@login_required
def delete():
    """
    Route for deleting list entries from database
    """

    # retrieve the id of the entry to delete and make sure it's not missing
    id = request.form.get("id")
    if not id:
        raise RuntimeError("missing parameter: id")

    # get the info to display to the user (which game was delete and under which platform it was)
    info = db_session.query(ListEntry.game, Platform.name).join(Platform).filter(ListEntry.id == id).one()
    info = { "game": info[0], "platform": info[1] }

    # delete the list entry
    db_session.query(ListEntry).filter(ListEntry.id == id).delete()
    db_session.commit()

    flash("{} under {} successfully deleted from your backlog.".format(info.get("game"), info.get("platform")), "success")
    return redirect(url_for("backlog"))

@login_manager.user_loader
def load_user(user_id):
    """
    https://flask-login.readthedocs.io/en/latest/
    """

    return User.query.get(user_id)

if __name__ == "__main__":
    app.run()
