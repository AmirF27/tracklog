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

# configure app
app = Flask(__name__)
app.secret_key = 'some_secret'

# configure login_manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"

# configure JSGlue
JSGlue(app)

@app.route("/")
def index():
    """
    Route for rendering the home page
    """

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

@app.route("/lists/<string:list_type>")
@login_required
def lists(list_type):
    """
    Route for displaying user backlog
    """

    # retrieve user's entries for current list (list_type)
    entries = db_session.query(ListEntry, Platform.name). \
                         join(Platform). \
                         filter(ListEntry.user_id == current_user.id). \
                         filter(ListEntry.list_type == list_type). \
                         order_by(ListEntry.game). \
                         all()

    # retrieve user's platforms
    platforms = db_session.query(Platform.name). \
                           join(UserPlatform). \
                           filter(UserPlatform.user_id == current_user.id). \
                           order_by(Platform.name). \
                           all()

    # render list (list_type) with user's entries and platforms
    return render_template("list.html", list_type=list_type, entries=entries, platforms=platforms)

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

@app.route("/add-game/<string:list_type>", methods=["POST"])
@login_required
def add_game(list_type):
    """
    Route to handle adding games to various lists
    """

    # retrieve form data
    platform = request.form.get("platform")
    igdb_id = request.form.get("igdb_id")
    game = request.form.get("game_name")
    image_url = request.form.get("image_url")

    # make sure none of the fields in the form were blank
    if not all([platform, igdb_id, game, image_url]) or platform == "Platform":
        flash("Game and/or platform missing, couldn't add to {}. Please try again.".format(list_type), "danger")
        return redirect(url_for("lists", list_type=list_type))

    # get platform ID from database based on the value provided in the form
    platform_id = db_session.query(Platform.id).filter(Platform.name == platform).one().id

    # query the database and check if the entry the user is about to add
    # already exists, in order to ensure the user doesn't add duplicates
    if not db_session.query(ListEntry).filter(ListEntry.user_id == current_user.id). \
                                       filter(ListEntry.game == game). \
                                       filter(ListEntry.platform_id == platform_id). \
                                       first():
        # if the entry doesn't exist in the database, insert it
        db_session.add(ListEntry(current_user.id, platform_id, igdb_id, game, image_url, list_type))
        db_session.commit()

    # if the entry is already in the database
    else:
        # redirect user to current list, displaying an error message
        flash("{} is already in your {} under {}.".format(game,list_type, platform), "danger")
        return redirect(url_for("lists", list_type=list_type))

    # redirect user to current list, displaying a success message
    flash("{} successfully added to your {} under {}.".format(game, list_type, platform), "success")
    return redirect(url_for("lists", list_type=list_type))

@app.route("/delete-game/<string:list_type>", methods=["POST"])
@login_required
def delete_game(list_type):
    """
    Route for deleting list entries from database
    """

    # retrieve the name of the game to delete and make sure it's not missing
    entry_game = request.form.get("entry_game")
    if not entry_game:
        raise RuntimeError("missing parameter: entry_game")

    # retrieve the platform of the game to delete and make sure it's not missing
    entry_platform = request.form.get("entry_platform")
    if not entry_platform:
        raise RuntimeError("missing parameter: entry_platform")

    # query database for the ID of the entry to delete
    entry_id = db_session.query(ListEntry.id). \
                          join(Platform). \
                          filter(ListEntry.list_type == list_type). \
                          filter(ListEntry.game == entry_game). \
                          filter(Platform.name == entry_platform). \
                          first()[0]

    # make sure the entry exists in the database
    if not entry_id:
        flash("Uh oh, something went wrong.", "danger")
        redirect(url_for("lists"), list_type=list_type)

    # delete the list entry
    db_session.query(ListEntry).filter(ListEntry.id == entry_id).delete()
    db_session.commit()

    # redirect user to the current list, displaying a success message
    flash("{} under {} successfully deleted from your {}."
        .format(entry_game, entry_platform, list_type), "success")
    return redirect(url_for("lists", list_type=list_type))

@app.route("/account-settings")
@login_required
def account_settings():

    platforms = []

    for platform in db_session.query(UserPlatform, Platform.name). \
                           join(Platform). \
                           filter(UserPlatform.user_id == current_user.id). \
                           order_by(Platform.name). \
                           all():
        platforms.append(platform[1])

    return render_template("account-settings.html", platforms=platforms)

@app.route("/delete-platform", methods=["POST"])
@login_required
def delete_platform():
    """
    Route for deleting platforms
    """

    # retrieve the platform name to delete and make sure it's not missing
    platform_name = request.form.get("platform_name")
    if not platform_name:
        raise RuntimeError("missing parameter: platform_name")

    # query database for the ID of the platform to delete
    platform_id = db_session.query(UserPlatform.id). \
                             join(Platform). \
                             filter(UserPlatform.id == current_user.id). \
                             filter(Platform.name == platform_name). \
                             first()[0]

    # make sure the platform exists in the database
    if not platform_id:
        flash("Uh oh, something went wrong.", "danger")
        return redirect(url_for("account_settings"))

    # delete platform
    db_session.query(UserPlatform).filter(UserPlatform.id == platform_id).delete()
    db_session.commit()

    # redirect user to their settings page, displaying a success message
    flash("{} successfully deleted.".format(platform_name), "success")
    return redirect(url_for("account_settings"))

@login_manager.user_loader
def load_user(user_id):
    """
    https://flask-login.readthedocs.io/en/latest/
    """

    return User.query.get(user_id)

if __name__ == "__main__":
    app.run()
