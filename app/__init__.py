"""App factory — wires together all blueprints, extensions, and config."""

import os

from flask import Flask, redirect, url_for

from app.config import get_config
from app.extensions import get_cache, limiter


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        A configured Flask app instance.
    """
    app = Flask(__name__)
    cfg = get_config()
    app.config.from_object(cfg)

    _validate_config(app)
    _ensure_data_dirs(app)

    limiter.init_app(app)

    from app.auth import auth_bp
    from app.chat import chat_bp
    from app.analysis import analysis_bp
    from app.study_plan import study_plan_bp
    from app.quiz import quiz_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(study_plan_bp)
    app.register_blueprint(quiz_bp)

    @app.route("/")
    def index():
        """Redirect root to the chat interface."""
        return redirect(url_for("chat.chat"))

    return app


def _validate_config(app: Flask) -> None:
    """Raise a clear error if any required environment variable is missing."""
    required = ["SECRET_KEY", "ANTHROPIC_API_KEY", "FERNET_KEY"]
    missing = [k for k in required if not app.config.get(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in all values."
        )


def _ensure_data_dirs(app: Flask) -> None:
    """Create data and cache directories at startup if they don't exist."""
    for key in ("USERS_DIR", "SESSIONS_DIR", "CACHE_DIR"):
        os.makedirs(app.config[key], exist_ok=True)
