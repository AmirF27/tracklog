from flask import Flask, render_template, request, redirect, url_for
from models import User
from passlib.apps import custom_app_context as pwd_context
from database import db_session

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

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

if __name__ == "__main__":
    app.run()
