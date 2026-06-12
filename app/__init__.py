"""App factory — wires together all blueprints, extensions, and config."""

import logging
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from app.config import get_config
from app.extensions import csrf, get_cache, limiter, mail

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
    csrf.init_app(app)

    from app.auth import auth_bp
    from app.chat import chat_bp
    from app.analysis import analysis_bp
    from app.study_plan import study_plan_bp
    from app.quiz import quiz_bp
    from app.profile import profile_bp
    from app.social import social_bp
    from app.billing import billing_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(study_plan_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(billing_bp)

    from app.storage import StorageCorruptError, load_user_cached

    @app.context_processor
    def inject_ui_prefs():
        """Inject per-user UI preference flags and social stats into all templates."""
        from app.social.xp_engine import level_progress
        from app.social.missions import get_or_refresh_missions

        mail_enabled = bool(app.config.get("MAIL_ENABLED"))
        email = session.get("email")

        _defaults = {
            "pomodoro_intro_dismissed": False,
            "logged_in": False,
            "display_name": "",
            "mail_enabled": mail_enabled,
            "streak_count": 0,
            "xp_info": {"level": 1, "league": "Bronze", "progress": 0, "needed": 100, "pct": 0},
            "missions": [],
            "current_tier": "free",
        }

        if not email:
            return _defaults

        try:
            user = load_user_cached(email)
        except StorageCorruptError:
            return {**_defaults, "logged_in": True, "display_name": email.split("@")[0]}

        if user is None:
            return {**_defaults, "logged_in": True, "display_name": email.split("@")[0]}

        display_name = user.get("username") or email.split("@")[0]
        from datetime import date as _date
        today_str = _date.today().isoformat()
        missions_list = user.get("missions", []) if user.get("missions_date") == today_str else []

        return {
            "pomodoro_intro_dismissed": bool(user.get("pomodoro_intro_dismissed_at")),
            "logged_in": True,
            "display_name": display_name,
            "mail_enabled": mail_enabled,
            "streak_count": user.get("streak_count", 0),
            "xp_info": level_progress(user.get("xp", 0)),
            "missions": missions_list,
            "current_tier": user.get("tier", "free"),
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
        # Prevent browsers from serving a stale cached page from a previous
        # login session. The nav renders server-side and varies by cookie, so
        # caching would cause the wrong links to appear on first visit.
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Vary"] = "Cookie"
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
        return redirect(url_for("index"))

    @app.errorhandler(500)
    def internal_error(e):
        """Return a safe error page without exposing stack traces."""
        logger.exception("Unhandled server error on %s", request.path)
        message = "Something went wrong on our end. Please try again in a moment."
        if request.path in ("/chat", "/history") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": message}), 500
        flash(message, "error")
        # Send the user back to the page they were on if possible, otherwise home.
        if request.path.startswith("/study-plan"):
            return redirect(url_for("study_plan.plan"))
        return redirect(url_for("index"))

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
