"""Auth utilities — password hashing and the login_required decorator."""

import functools
from typing import Any

import bcrypt
from flask import flash, jsonify, redirect, session, url_for

from app.storage import StorageCorruptError, load_session, load_user


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt.

    Args:
        plain: The user's raw password string.

    Returns:
        A bcrypt hash string safe to store in the user record.
    """
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash.

    Args:
        plain: The raw password to verify.
        hashed: The stored bcrypt hash string.

    Returns:
        True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _clear_session_and_message() -> None:
    """Clear the Flask session after unrecoverable account data loss."""
    session.clear()
    flash(StorageCorruptError.USER_MESSAGE, "error")


def force_logout_redirect():
    """Clear session and redirect to login after missing or corrupt user data."""
    _clear_session_and_message()
    return redirect(url_for("auth.login"))


def force_logout_json():
    """Return a JSON 401 after missing or corrupt user data."""
    session.clear()
    return jsonify({"error": StorageCorruptError.USER_MESSAGE}), 401


def load_session_for_api(email: str) -> tuple[dict | None, Any]:
    """Load session data for a JSON API route or return a 401 response.

    Returns:
        (session_dict, None) on success, or (None, json_response) on failure.
    """
    try:
        return load_session(email), None
    except StorageCorruptError:
        return None, force_logout_json()


def get_current_user() -> tuple[dict | None, Any]:
    """Load the logged-in user or return a redirect response.

    Returns:
        (user_dict, None) on success, or (None, redirect_response) on failure.
    """
    email = session.get("email")
    if not email:
        return None, redirect(url_for("auth.login"))
    try:
        user = load_user(email)
    except StorageCorruptError:
        return None, force_logout_redirect()
    if user is None:
        return None, force_logout_redirect()
    return user, None


def get_current_user_for_api() -> tuple[dict | None, Any]:
    """Load the logged-in user for a JSON route or return a 401 response.

    Returns:
        (user_dict, None) on success, or (None, json_response) on failure.
    """
    email = session.get("email")
    if not email:
        return None, (jsonify({"error": "Not authenticated."}), 401)
    try:
        user = load_user(email)
    except StorageCorruptError:
        return None, force_logout_json()
    if user is None:
        return None, force_logout_json()
    return user, None


def login_required(f):
    """Decorator that redirects unauthenticated users to the login page."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        """Enforce authentication before calling the wrapped view."""
        if "email" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return wrapper
