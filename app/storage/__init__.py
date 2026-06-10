"""Public API for the storage module."""

from app.storage.errors import StorageCorruptError
from app.storage.session_store import delete_session, load_session, save_session
from app.storage.user_store import delete_user, load_user, save_user, user_exists

__all__ = [
    "StorageCorruptError",
    "load_user",
    "save_user",
    "delete_user",
    "user_exists",
    "load_session",
    "save_session",
    "delete_session",
]
