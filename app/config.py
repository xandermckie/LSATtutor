"""Flask configuration classes — all secrets read from environment variables."""

import os


class BaseConfig:
    """Shared configuration for all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    FERNET_KEY = os.environ.get("FERNET_KEY")

    # Rate limiting defaults (requests per hour per IP)
    RATELIMIT_DEFAULT = "100 per hour"
    CHAT_RATELIMIT = "20 per hour"
    AUTH_RATELIMIT = "10 per hour"

    # Context compression: compress when session exceeds this many turns
    CONTEXT_COMPRESSION_THRESHOLD = 10
    CONTEXT_TURNS_TO_COMPRESS = 5

    _repo_root = os.path.dirname(os.path.dirname(__file__))
    DATA_DIR = os.environ.get(
        "DATA_DIR",
        os.path.join(_repo_root, "data"),
    )
    USERS_DIR = os.path.join(DATA_DIR, "users")
    SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
    AVATARS_DIR = os.path.join(DATA_DIR, "avatars")
    CACHE_DIR = os.environ.get(
        "CACHE_DIR",
        os.path.join(_repo_root, "cache"),
    )

    MAX_AVATAR_BYTES = 2 * 1024 * 1024   # 2 MB
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024  # Flask hard limit before route runs

    # Email — Gmail SMTP via Flask-Mail
    MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "false").lower() == "true"
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "contact.ratio.tutor@gmail.com")
    # Strip spaces — Gmail App Passwords are displayed with spaces but sent without
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "").replace(" ", "")
    MAIL_DEFAULT_SENDER = ("Ratio LSAT Tutor", os.environ.get("MAIL_USERNAME", "contact.ratio.tutor@gmail.com"))
    # Prevent SMTP hangs — 15-second connect+read timeout per operation
    MAIL_TIMEOUT = 15


class DevelopmentConfig(BaseConfig):
    """Development environment — debug on, relaxed limits."""

    DEBUG = True
    TESTING = False


class ProductionConfig(BaseConfig):
    """Production environment — debug off, strict limits."""

    DEBUG = False
    TESTING = False
    CHAT_RATELIMIT = "20 per hour"


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    """Return the appropriate config class based on FLASK_ENV."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
