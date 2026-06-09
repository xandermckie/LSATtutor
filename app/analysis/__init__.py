"""Analysis blueprint registration."""

from flask import Blueprint

analysis_bp = Blueprint("analysis", __name__)

from app.analysis import routes  # noqa: E402, F401
