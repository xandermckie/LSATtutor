"""Breaking tests — deliberate failure scenarios and resilience checks."""

import hashlib
import io
import os

import pytest

from app.storage import load_session
from app.storage.errors import StorageCorruptError
from tests.conftest import login_client, register_user


def _user_enc_path(dirs: dict, email: str) -> str:
    """Return the encrypted user file path for an email."""
    hashed = hashlib.sha256(email.lower().encode()).hexdigest()
    return os.path.join(dirs["users_dir"], f"{hashed}.enc")


def _session_enc_path(dirs: dict, email: str) -> str:
    """Return the encrypted session file path for an email."""
    hashed = hashlib.sha256(email.lower().encode()).hexdigest()
    return os.path.join(dirs["sessions_dir"], f"{hashed}.enc")


def test_empty_chat_message_returns_400(app_client):
    """Empty and whitespace-only messages are rejected."""
    app, client, _dirs = app_client
    register_user(app, "chat@example.com")
    login_client(client, "chat@example.com")

    for payload in [{"message": ""}, {"message": "   "}]:
        response = client.post("/chat", json=payload)
        assert response.status_code == 400
        assert response.get_json()["error"] == "Message is required."


def test_oversized_chat_message_returns_400(app_client):
    """Messages over 3,000 characters are rejected."""
    app, client, _dirs = app_client
    register_user(app, "long@example.com")
    login_client(client, "long@example.com")

    response = client.post("/chat", json={"message": "x" * 3001})
    assert response.status_code == 400
    assert "too long" in response.get_json()["error"].lower()


def test_special_characters_chat_message(app_client, monkeypatch):
    """Special-character-only input is accepted when the API succeeds."""
    app, client, _dirs = app_client
    register_user(app, "special@example.com")
    login_client(client, "special@example.com")

    def fake_call_claude(messages, system, cache_dir):
        return "Handled special input.", True

    monkeypatch.setattr("app.chat.routes.call_claude", fake_call_claude)

    response = client.post("/chat", json={"message": "!@#$%^&*()"})
    assert response.status_code == 200
    assert response.get_json()["response"] == "Handled special input."


def test_api_authentication_error_returns_friendly_message(app_client, monkeypatch):
    """Invalid API key surfaces a friendly error without a 500."""
    app, client, _dirs = app_client
    register_user(app, "authfail@example.com")
    login_client(client, "authfail@example.com")

    def fake_call_claude(messages, system, cache_dir):
        return "API authentication failed. Please contact support.", False

    monkeypatch.setattr("app.chat.routes.call_claude", fake_call_claude)

    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 503
    assert "authentication failed" in response.get_json()["error"].lower()


def test_api_connection_error_does_not_consume_quota(app_client, monkeypatch):
    """Network failures return an error without incrementing the daily quota."""
    app, client, _dirs = app_client
    email = "offline@example.com"
    register_user(app, email)
    login_client(client, email)

    def fake_call_claude(messages, system, cache_dir):
        return "Could not reach the tutoring service. Please check your connection and try again.", False

    monkeypatch.setattr("app.chat.routes.call_claude", fake_call_claude)

    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 503

    with app.app_context():
        session_data = load_session(email)
    assert session_data.get("chat_usage", {}).get("count", 0) == 0
    assert session_data.get("turns", []) == []


def test_deleted_user_file_redirects_to_login(app_client):
    """Orphaned sessions redirect to login instead of crashing."""
    app, client, dirs = app_client
    email = "orphan@example.com"
    register_user(app, email)
    login_client(client, email)
    os.remove(_user_enc_path(dirs, email))

    response = client.get("/profile/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_corrupt_session_file_returns_401_on_chat(app_client):
    """Corrupt session data forces re-authentication on JSON routes."""
    app, client, dirs = app_client
    email = "corrupt@example.com"
    register_user(app, email)
    login_client(client, email)

    os.makedirs(dirs["sessions_dir"], exist_ok=True)
    session_path = _session_enc_path(dirs, email)
    with open(session_path, "wb") as f:
        f.write(b"not-valid-ciphertext")

    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 401
    assert "could not be read" in response.get_json()["error"].lower()


def test_corrupt_user_file_redirects_to_login(app_client):
    """Corrupt user data forces logout on HTML routes."""
    app, client, dirs = app_client
    email = "baduser@example.com"
    register_user(app, email)
    login_client(client, email)

    with open(_user_enc_path(dirs, email), "wb") as f:
        f.write(b"garbage-data")

    response = client.get("/profile/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_invalid_avatar_upload_shows_error(app_client):
    """Fake image uploads are rejected with a friendly flash message."""
    app, client, _dirs = app_client
    register_user(app, "avatar@example.com")
    login_client(client, "avatar@example.com")

    data = {
        "avatar": (io.BytesIO(b"not an image"), "photo.png"),
    }
    response = client.post(
        "/profile/avatar/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"does not appear to be a valid PNG or JPEG" in response.data


def test_invalid_ics_duration_shows_error(app_client):
    """Non-numeric calendar duration is rejected without a 500."""
    app, client, _dirs = app_client
    register_user(app, "ics@example.com")
    login_client(client, "ics@example.com")

    response = client.post(
        "/study-plan/export.ics",
        data={"duration": "not-a-number", "days": ["Mon"]},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"whole number of minutes" in response.data


def test_missing_data_directories_are_created(app_client):
    """Saving user data creates storage directories when they do not exist."""
    app, _client, dirs = app_client
    nested_users = os.path.join(dirs["users_dir"], "nested", "accounts")
    app.config["USERS_DIR"] = nested_users

    with app.app_context():
        from app.storage import save_user
        save_user("nested@example.com", {
            "email": "nested@example.com",
            "password_hash": "hash",
            "target_exam_date": None,
            "username": "",
            "agreed_to_terms_at": "2026-01-01T00:00:00+00:00",
            "birth_year_verified": True,
        })

    assert os.path.isdir(nested_users)


def test_load_user_raises_storage_corrupt_error(app_client):
    """Corrupt ciphertext raises StorageCorruptError from the storage layer."""
    app, _client, dirs = app_client
    email = "storage@example.com"
    register_user(app, email)

    with open(_user_enc_path(dirs, email), "wb") as f:
        f.write(b"broken")

    with app.app_context():
        with pytest.raises(StorageCorruptError):
            from app.storage import load_user
            load_user(email)
