import os
import unirest
import urllib2
import urllib

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, current_user
from sqlalchemy import func, or_
from passlib.apps import custom_app_context as pwd_context
from models import *
from database import db_session
from helpers import *
from flask_jsglue import JSGlue

import traceback

# configure app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

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
            flash("You've entered a wrong password.")
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
            return redirect(url_for("register"))

        # make sure password and password confirmation match
        if password != confirm:
            flash("Password and password confirmation did not match.")
            return redirect(url_for("register"))

        # query database to check whether username/email already exist
        if db_session.query(User). \
                      filter(or_(User.username == username, User.email == email)). \
                      first():
            flash("The username and/or email address you've entered already exist.")
            return redirect(url_for("register"))

        # everything went well, add user to database
        user = User(username, email, pwd_context.encrypt(password))
        db_session.add(user)
        db_session.commit()

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

    # retrieve user's platforms
    platforms = db_session.query(Platform.name). \
                           join(UserPlatform). \
                           filter(UserPlatform.user_id == current_user.id). \
                           order_by(Platform.name). \
                           all()

    # retrieve user's entries for current list (list_type)
    entries = db_session.query(ListEntry, Game, Platform.name). \
                         join(Game). \
                         join(Platform). \
                         filter(ListEntry.user_id == current_user.id). \
                         filter(ListEntry.list_type == list_type). \
                         order_by(Platform.name, Game.name). \
                         all()

    # if the user's current list (list_type) is not emptry
    if entries:
        # https://developmentality.wordpress.com/2012/03/30/three-ways-of-creating-dictionaries-in-python/
        games = dict([ (platform.name, []) for platform in platforms ])
        for entry in entries:
            games[entry[2]].append(entry[1])
    else:
        games = None

    # render list (list_type) with user's entries and platforms
    return render_template("list.html", list_type=list_type, games=games, platforms=platforms)

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
    return jsonify(results=response)

@app.route("/add-game/<string:list_type>", methods=["POST"])
@login_required
def add_game(list_type):
    """
    Route to handle adding games to various lists
    """

    # retrieve form data
    platform = request.form.get("platform")
    igdb_id = request.form.get("igdb_id")
    game_name = request.form.get("game_name")
    image_url = request.form.get("image_url")

    # make sure none of the fields in the form were blank
    if not all([platform, igdb_id]) or platform == "Platform":
        flash("Game and/or platform missing, couldn't add to your {}. Please try again.".format(list_type), "danger")
        return redirect(url_for("lists", list_type=list_type))

    # get platform ID from database based on the value provided in the form
    platform_id = db_session.query(Platform).filter(Platform.name == platform).first().id

    # query database for requested game
    game = db_session.query(Game).filter(Game.igdb_id == igdb_id).first()

    # if the game doesn't exist in the database, insert it
    if not game:
        game = Game(igdb_id, game_name, image_url)
        db_session.add(game)
        db_session.commit()

    # query the database and check if the entry the user is about to add
    # already exists, in order to ensure the user doesn't add duplicates
    if not db_session.query(ListEntry).filter(ListEntry.user_id == current_user.id). \
                                       filter(ListEntry.game_id == game.id). \
                                       filter(ListEntry.platform_id == platform_id). \
                                       first():
        # if the entry doesn't exist in the database, insert it
        db_session.add(ListEntry(current_user.id, game.id, platform_id, list_type))
        db_session.commit()
    # if the entry is already in the database
    else:
        # redirect user to current list, displaying an error message
        flash("{} is already in your {} under {}.".format(game.name,list_type, platform), "danger")
        return redirect(url_for("lists", list_type=list_type))

    # redirect user to current list, displaying a success message
    flash("{} successfully added to your {} under {}.".format(game.name, list_type, platform), "success")
    return redirect(url_for("lists", list_type=list_type))

@app.route("/delete-game/<string:list_type>", methods=["POST"])
@login_required
def delete_game(list_type):
    """
    Route for deleting list entries from database
    """

    # retrieve the name of the game to delete and make sure it's not missing
    igdb_id = request.form.get("igdb_id")
    if not igdb_id:
        raise RuntimeError("missing parameter: igdb_id")

    # retrieve the platform of the game to delete and make sure it's not missing
    platform = request.form.get("platform")
    if not platform:
        raise RuntimeError("missing parameter: platform")

    # query database for the ID of the entry to delete, as well as 
    # the associated game name
    entry = db_session.query(ListEntry.id, Game.name). \
                          join(Game). \
                          join(Platform). \
                          filter(ListEntry.list_type == list_type). \
                          filter(Game.igdb_id == igdb_id). \
                          filter(Platform.name == platform). \
                          first()

    # make sure the entry exists in the database
    if not entry.id:
        flash("Uh oh, something went wrong.", "danger")
        redirect(url_for("lists"), list_type=list_type)

    # delete the list entry
    db_session.query(ListEntry).filter(ListEntry.id == entry.id).delete()
    db_session.commit()

    # redirect user to the current list, displaying a success message
    flash("{} under {} successfully deleted from your {}."
        .format(entry.name, platform, list_type), "success")
    return redirect(url_for("lists", list_type=list_type))

@app.route("/account-settings")
@login_required
def account_settings():
    """
    Route for fetching user's data and displaying their settings page
    """

    # query database for user's platforms
    user_platforms = db_session.query(UserPlatform, Platform.name). \
                                join(Platform). \
                                filter(UserPlatform.user_id == current_user.id). \
                                order_by(Platform.name). \
                                with_entities(Platform.name). \
                                all()

    # query database for all existing platforms
    platforms = db_session.query(Platform.name). \
                           order_by(Platform.name). \
                           all()

    return render_template("account-settings.html", user_platforms=user_platforms, platforms=platforms)

@app.route("/change-email", methods=["POST"])
@login_required
def change_email():
    """
    Route for changing email address
    """

    # retrieve password and email and make sure they're not missing
    password = request.form.get("password")
    email = request.form.get("email")
    if not all([password, email]):
        flash("Password and/or email address missing.", "danger")
        return redirect(url_for("account_settings"))

    # make sure the password the user has entered is correct
    if not pwd_context.verify(password, current_user.password):
        flash("You've entered a wrong password.", "danger")
        return redirect(url_for("account_settings"))

    # change the user's email address
    User.query.get(current_user.id).email = email
    db_session.commit()

    # redirect the user to their settings page with a success message
    flash("Email address successfully changed.", "success")
    return redirect(url_for("account_settings"))

@app.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """
    Route for changing password
    """

    # retrieve current and new password and password confirmation 
    # and make sure they're not missing
    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")
    if not all([current_password, new_password, confirm_password]):
        flash("Current password, new password, and/or password confirmation missing", "danger")
        return redirect(url_for("account_settings"))

    # make sure the current password is correct
    if not pwd_context.verify(current_password, current_user.password):
        flash("You've entered a wrong current password.", "danger")
        return redirect(url_for("account_settings"))

    # make sure new password and new password confirmation match
    if new_password != confirm_password:
        flash("New password and new password confirmation did not match.", "danger")
        return redirect(url_for("account_settings"))

    # change the user's password
    User.query.get(current_user.id).password = pwd_context.encrypt(new_password)
    db_session.commit()

    # redirect the user to their settings page with a success message
    flash("Password successfully changed.", "success")
    return redirect(url_for("account_settings"))

@app.route("/add-platform", methods=["POST"])
@login_required
def add_platform():
    """
    Route for adding platforms
    """

    # retrieve the platform name to add and make sure it's not missing
    platform_name = request.form.get("platform_name")
    if not platform_name:
        raise RuntimeError("missing parameter: platform_name")

    # query database for requested platform, making sure to perform a case-insensitive
    # search (the user could have typed in all lower case, for instance)
    platform = db_session.query(Platform). \
                             filter(func.lower(Platform.name) == func.lower(platform_name)). \
                             first()

    # make sure the requested platform exists in the database
    if not platform:
        flash("You've entered an invalid platform name. Please try again.", "danger")
        return redirect(url_for("account_settings"))

    # get the platform ID and proper name from database
    platform_id = platform.id
    platform_name = platform.name

    # query the database and check if the platform the user is about to add
    # already exists, in order to ensure the user doesn't add duplicates
    if not db_session.query(UserPlatform). \
                      filter(UserPlatform.user_id == current_user.id). \
                      filter(UserPlatform.platform_id == platform_id). \
                      first():
        # if the entry doesn't exist in the database, insert it
        db_session.add(UserPlatform(current_user.id, platform_id))
        db_session.commit()
    # if the entry is already in the database
    else:
        # redirect user to current list, displaying an error message
        flash("You already have {} in your platforms.".format(platform_name), "danger")
        return redirect(url_for("account_settings"))

    # redirect user to their settings page, displaying a success message
    flash("{} successfully added to your platforms.".format(platform_name), "success")
    return redirect(url_for("account_settings"))

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
    platform_id = db_session.query(UserPlatform.id, Platform.id). \
                             join(Platform). \
                             filter(UserPlatform.user_id == current_user.id). \
                             filter(Platform.name == platform_name). \
                             first()

    # make sure the platform exists in the database
    if not platform_id[0]:
        flash("Uh oh, something went wrong.", "danger")
        return redirect(url_for("account_settings"))

    # delete all games associated with platform
    db_session.query(ListEntry).filter(ListEntry.user_id == current_user.id). \
                                filter(ListEntry.platform_id == platform_id[1]). \
                                delete()
    # delete platform
    db_session.query(UserPlatform).filter(UserPlatform.id == platform_id[0]).delete()
    db_session.commit()

    # redirect user to their settings page, displaying a success message
    flash("{} successfully deleted from your platforms.".format(platform_name), "success")
    return redirect(url_for("account_settings"))

@login_manager.user_loader
def load_user(user_id):
    """
    https://flask-login.readthedocs.io/en/latest/
    """

    return User.query.get(user_id)

if __name__ == "__main__":
    app.run()
