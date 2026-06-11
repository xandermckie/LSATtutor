"""Social features blueprint — leaderboard, friends, challenges, XP."""

from flask import Blueprint

social_bp = Blueprint("social", __name__)

from app.social import routes  # noqa: F401, E402
