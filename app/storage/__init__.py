"""Public API for the storage module."""

from flask import g

from app.storage.errors import StorageCorruptError
from app.storage.session_store import delete_session, load_session, save_session
from app.storage.user_store import delete_user, load_user, save_user, user_exists


def load_user_cached(email: str) -> dict | None:
    """Load a user record, caching the result in Flask's per-request g object.

    Subsequent calls within the same request return the cached dict without
    hitting disk again. Call save_user() directly to persist mutations; the
    cache is intentionally not invalidated automatically so callers that mutate
    and save can continue using their reference.

    Args:
        email: The user's email address.

    Returns:
        The user dict, or None if the user does not exist.
    """
    cache = g.setdefault("_user_cache", {})
    key = email.lower()
    if key not in cache:
        cache[key] = load_user(email)
    return cache[key]


def invalidate_user_cache(email: str) -> None:
    """Remove a user from the per-request cache after a save.

    Args:
        email: The user's email address.
    """
    cache = g.get("_user_cache", {})
    cache.pop(email.lower(), None)


__all__ = [
    "StorageCorruptError",
    "load_user",
    "load_user_cached",
    "invalidate_user_cache",
    "save_user",
    "delete_user",
    "user_exists",
    "load_session",
    "save_session",
    "delete_session",
]
