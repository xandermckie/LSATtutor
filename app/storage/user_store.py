"""CRUD operations for user account JSON files."""

import hashlib
import json
import logging
import os

from cryptography.fernet import InvalidToken
from flask import current_app

from app.storage.encryption import decrypt_data, encrypt_data
from app.storage.errors import StorageCorruptError

logger = logging.getLogger(__name__)


def _user_path(email: str) -> str:
    """Return the file path for a user's encrypted JSON file, keyed by hashed email."""
    hashed = hashlib.sha256(email.lower().encode()).hexdigest()
    return os.path.join(current_app.config["USERS_DIR"], f"{hashed}.enc")


def load_user(email: str) -> dict | None:
    """Load and decrypt a user record by email.

    Returns:
        The user dict, or None if the user does not exist.

    Raises:
        EnvironmentError: If FERNET_KEY is missing.
        cryptography.fernet.InvalidToken: If the stored data is corrupt.
    """
    path = _user_path(email)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return decrypt_data(f.read())
    except (InvalidToken, json.JSONDecodeError) as exc:
        logger.exception("Corrupt user data at %s", os.path.basename(path))
        raise StorageCorruptError(str(exc)) from exc
    except OSError as exc:
        logger.exception("Failed to read user data at %s", os.path.basename(path))
        raise StorageCorruptError(str(exc)) from exc


def save_user(email: str, user_data: dict) -> None:
    """Encrypt and write a user record to disk.

    Args:
        email: The user's email address (used to derive the filename).
        user_data: The user dict to persist.

    Raises:
        EnvironmentError: If FERNET_KEY is missing.
    """
    os.makedirs(current_app.config["USERS_DIR"], exist_ok=True)
    path = _user_path(email)
    with open(path, "wb") as f:
        f.write(encrypt_data(user_data))


def delete_user(email: str) -> None:
    """Remove a user's encrypted data file from disk.

    Does nothing if the file does not exist.
    """
    path = _user_path(email)
    if os.path.exists(path):
        os.remove(path)


def user_exists(email: str) -> bool:
    """Return True if an account file exists for the given email."""
    return os.path.exists(_user_path(email))
