"""Input validation for auth forms."""

import re


def validate_register(email: str, password: str, confirm: str) -> list[str]:
    """Validate registration fields and return a list of error strings.

    Args:
        email: Submitted email address.
        password: Submitted password.
        confirm: Password confirmation field.

    Returns:
        A list of human-readable error messages; empty list means valid.
    """
    errors = []
    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("A valid email address is required.")
    if not password or len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != confirm:
        errors.append("Passwords do not match.")
    return errors


def validate_login(email: str, password: str) -> list[str]:
    """Validate login fields and return a list of error strings.

    Args:
        email: Submitted email address.
        password: Submitted password.

    Returns:
        A list of human-readable error messages; empty list means valid.
    """
    errors = []
    if not email:
        errors.append("Email is required.")
    if not password:
        errors.append("Password is required.")
    return errors
