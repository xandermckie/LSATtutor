"""Tests for Pomodoro intro popup dismissal and per-account persistence."""

from app.storage import load_user
from tests.conftest import login_client, register_user


def test_context_shows_not_dismissed_for_new_user(app_client):
    """Logged-in users without the flag see pomodoroIntroDismissed as false."""
    app, client, _dirs = app_client
    email = "pomodoro@example.com"
    register_user(app, email)
    login_client(client, email)

    response = client.get("/")
    assert response.status_code == 200
    assert b"pomodoroIntroDismissed: false" in response.data


def test_dismiss_endpoint_sets_user_field(app_client):
    """POST dismiss persists pomodoro_intro_dismissed_at on the user record."""
    app, client, _dirs = app_client
    email = "dismiss@example.com"
    register_user(app, email)
    login_client(client, email)

    response = client.post("/profile/pomodoro-intro/dismiss")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}

    with app.app_context():
        user = load_user(email)
    assert user.get("pomodoro_intro_dismissed_at")


def test_dismiss_endpoint_is_idempotent(app_client):
    """A second dismiss request still succeeds without changing the timestamp."""
    app, client, _dirs = app_client
    email = "idempotent@example.com"
    register_user(app, email)
    login_client(client, email)

    client.post("/profile/pomodoro-intro/dismiss")
    with app.app_context():
        user_after_first = load_user(email)
    first_ts = user_after_first["pomodoro_intro_dismissed_at"]

    response = client.post("/profile/pomodoro-intro/dismiss")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}

    with app.app_context():
        user_after_second = load_user(email)
    assert user_after_second["pomodoro_intro_dismissed_at"] == first_ts


def test_context_shows_dismissed_after_save(app_client):
    """Template flag is true once the user record has been dismissed."""
    app, client, _dirs = app_client
    email = "done@example.com"
    register_user(app, email)
    login_client(client, email)

    client.post("/profile/pomodoro-intro/dismiss")
    response = client.get("/")
    assert response.status_code == 200
    assert b"pomodoroIntroDismissed: true" in response.data


def test_dismiss_requires_login(app_client):
    """Unauthenticated users are redirected to login."""
    _app, client, _dirs = app_client
    response = client.post("/profile/pomodoro-intro/dismiss")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
