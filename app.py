from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user
from sqlalchemy import func
from passlib.apps import custom_app_context as pwd_context
from models import User
from database import db_session
from helpers import *

app = Flask(__name__)
app.secret_key = 'some_secret'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"

@app.route("/")
@login_required
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

        next = request.args.get('next')

        if not is_safe_url(next):
            return abort(400)

        return redirect(next or url_for('index'))

        return redirect(url_for("index"))
    else:
        return render_template("login.html")

@app.route("/logout")
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

        return redirect(url_for("index"))
    else:
        return render_template("register.html")

@login_manager.user_loader
def load_user(user_id):
    """
    https://flask-login.readthedocs.io/en/latest/
    """

    return User.query.get(user_id)

if __name__ == "__main__":
    app.run()
