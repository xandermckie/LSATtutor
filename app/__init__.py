"""App factory — wires together all blueprints, extensions, and config."""

import logging
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from app.config import get_config
from app.extensions import get_cache, limiter, mail

logger = logging.getLogger(__name__)


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
    mail.init_app(app)

    from app.auth import auth_bp
    from app.chat import chat_bp
    from app.analysis import analysis_bp
    from app.study_plan import study_plan_bp
    from app.quiz import quiz_bp
    from app.profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(study_plan_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(profile_bp)

    from app.storage import StorageCorruptError, load_user_cached

    @app.context_processor
    def inject_ui_prefs():
        """Inject per-user UI preference flags into all templates."""
        mail_enabled = bool(app.config.get("MAIL_ENABLED"))
        email = session.get("email")
        if not email:
            return {
                "pomodoro_intro_dismissed": False,
                "logged_in": False,
                "display_name": "",
                "mail_enabled": mail_enabled,
            }
        try:
            user = load_user_cached(email)
        except StorageCorruptError:
            return {
                "pomodoro_intro_dismissed": False,
                "logged_in": True,
                "display_name": email.split("@")[0],
                "mail_enabled": mail_enabled,
            }
        if user is None:
            return {
                "pomodoro_intro_dismissed": False,
                "logged_in": True,
                "display_name": email.split("@")[0],
                "mail_enabled": mail_enabled,
            }
        display_name = user.get("username") or email.split("@")[0]
        return {
            "pomodoro_intro_dismissed": bool(user.get("pomodoro_intro_dismissed_at")),
            "logged_in": True,
            "display_name": display_name,
            "mail_enabled": mail_enabled,
        }

    @app.route("/")
    def index():
        """Show the marketing homepage."""
        return render_template("home.html")

    @app.after_request
    def set_security_headers(response):
        """Attach security headers to every response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        return response

    @app.errorhandler(413)
    def file_too_large(e):
        """Handle file uploads that exceed MAX_CONTENT_LENGTH."""
        flash("Uploaded file is too large. Maximum size is 2 MB.", "error")
        return redirect(url_for("profile.profile"))

    @app.errorhandler(429)
    def rate_limited(e):
        """Handle Flask-Limiter rate limit responses with a friendly message."""
        message = getattr(e, "description", None) or "Too many requests. Please wait and try again."
        if request.path in ("/chat", "/history") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": message}), 429
        flash(message, "error")
        return redirect(request.referrer or url_for("index"))

    @app.errorhandler(500)
    def internal_error(e):
        """Return a safe error page without exposing stack traces."""
        logger.exception("Unhandled server error on %s", request.path)
        message = "Something went wrong on our end. Please try again in a moment."
        if request.path in ("/chat", "/history") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": message}), 500
        flash(message, "error")
        return redirect(request.referrer or url_for("index")), 500

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
    for key in ("USERS_DIR", "SESSIONS_DIR", "CACHE_DIR", "AVATARS_DIR"):
        os.makedirs(app.config[key], exist_ok=True)
