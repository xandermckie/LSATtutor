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

    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    USERS_DIR = os.path.join(DATA_DIR, "users")
    SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")


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
