"""Auth utilities — password hashing and the login_required decorator."""

import functools

import bcrypt
from flask import redirect, session, url_for


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


def login_required(f):
    """Decorator that redirects unauthenticated users to the login page."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        """Enforce authentication before calling the wrapped view."""
        if "email" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return wrapper
