"""Study plan blueprint registration."""

from flask import Blueprint

study_plan_bp = Blueprint("study_plan", __name__)

from app.study_plan import routes  # noqa: E402, F401
