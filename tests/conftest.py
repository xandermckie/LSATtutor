"""Shared pytest fixtures for integration tests."""

import os
import tempfile

import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-api-key")

from app import create_app
from app.auth.helpers import hash_password
from app.storage import save_user


@pytest.fixture
def app_client(monkeypatch):
    """Create a Flask test client with isolated data directories."""
    fernet_key = Fernet.generate_key().decode()
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
    monkeypatch.setenv("FERNET_KEY", fernet_key)

    with tempfile.TemporaryDirectory() as tmp:
        users_dir = os.path.join(tmp, "users")
        sessions_dir = os.path.join(tmp, "sessions")
        avatars_dir = os.path.join(tmp, "avatars")
        cache_dir = os.path.join(tmp, "cache")

        app = create_app()
        app.config.update(
            TESTING=True,
            USERS_DIR=users_dir,
            SESSIONS_DIR=sessions_dir,
            AVATARS_DIR=avatars_dir,
            CACHE_DIR=cache_dir,
        )

        with app.test_client() as client:
            yield app, client, {
                "users_dir": users_dir,
                "sessions_dir": sessions_dir,
                "avatars_dir": avatars_dir,
                "cache_dir": cache_dir,
                "fernet_key": fernet_key,
            }


def register_user(app, email: str, password: str = "password123") -> None:
    """Save a minimal user record for testing."""
    with app.app_context():
        save_user(email, {
            "email": email,
            "password_hash": hash_password(password),
            "target_exam_date": None,
            "username": "",
            "agreed_to_terms_at": "2026-01-01T00:00:00+00:00",
            "birth_year_verified": True,
        })


def login_client(client, email: str) -> None:
    """Set the Flask session email for an authenticated user."""
    with client.session_transaction() as sess:
        sess["email"] = email
