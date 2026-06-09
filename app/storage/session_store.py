"""CRUD operations for per-user session/history JSON files."""

import hashlib
import os

from flask import current_app

from app.storage.encryption import decrypt_data, encrypt_data


def _session_path(email: str) -> str:
    """Return the file path for a user's session history file, keyed by hashed email."""
    hashed = hashlib.sha256(email.lower().encode()).hexdigest()
    return os.path.join(current_app.config["SESSIONS_DIR"], f"{hashed}.enc")


def load_session(email: str) -> dict:
    """Load and decrypt a user's session history.

    Returns:
        The session dict, or a blank session if none exists yet.

    Raises:
        EnvironmentError: If FERNET_KEY is missing.
        cryptography.fernet.InvalidToken: If the stored data is corrupt.
    """
    path = _session_path(email)
    if not os.path.exists(path):
        return {"turns": [], "summary": "", "weak_areas": {}}
    with open(path, "rb") as f:
        return decrypt_data(f.read())


def save_session(email: str, session_data: dict) -> None:
    """Encrypt and write a user's session history to disk.

    Args:
        email: The user's email address.
        session_data: The full session dict to persist.

    Raises:
        EnvironmentError: If FERNET_KEY is missing.
    """
    os.makedirs(current_app.config["SESSIONS_DIR"], exist_ok=True)
    path = _session_path(email)
    with open(path, "wb") as f:
        f.write(encrypt_data(session_data))


def delete_session(email: str) -> None:
    """Remove a user's session history file from disk.

    Does nothing if the file does not exist.
    """
    path = _session_path(email)
    if os.path.exists(path):
        os.remove(path)
