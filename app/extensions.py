"""Shared extension singletons — imported by blueprints to avoid circular imports."""

import os

import diskcache
from cryptography.fernet import Fernet
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def get_cache(cache_dir: str) -> diskcache.Cache:
    """Create and return a diskcache Cache instance at the given directory."""
    os.makedirs(cache_dir, exist_ok=True)
    return diskcache.Cache(cache_dir)


def get_fernet() -> Fernet:
    """Load the Fernet key from the environment and return a Fernet instance.

    Raises:
        EnvironmentError: If FERNET_KEY is not set.
        ValueError: If the key is malformed.
    """
    raw_key = os.environ.get("FERNET_KEY")
    if not raw_key:
        raise EnvironmentError(
            "FERNET_KEY environment variable is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(raw_key.encode())
