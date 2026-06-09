"""Auth routes — register, login, logout."""

from flask import redirect, render_template, request, session, url_for

from app.auth import auth_bp
from app.auth.forms import validate_login, validate_register
from app.auth.helpers import hash_password, verify_password
from app.extensions import limiter
from app.storage import load_user, save_user, user_exists


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    """Render and process the registration form."""
    errors = []
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        errors = validate_register(email, password, confirm)
        if not errors:
            if user_exists(email):
                errors.append("An account with that email already exists.")
            else:
                save_user(email, {
                    "email": email,
                    "password_hash": hash_password(password),
                    "target_exam_date": None,
                })
                session["email"] = email
                return redirect(url_for("chat.chat"))

    return render_template("auth/register.html", errors=errors)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def login():
    """Render and process the login form."""
    errors = []
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        errors = validate_login(email, password)
        if not errors:
            user = load_user(email)
            if user is None or not verify_password(password, user["password_hash"]):
                errors.append("Invalid email or password.")
            else:
                session["email"] = email
                return redirect(url_for("chat.chat"))

    return render_template("auth/login.html", errors=errors)


@auth_bp.route("/logout")
def logout():
    """Clear the session and redirect to login."""
    session.clear()
    return redirect(url_for("auth.login"))
