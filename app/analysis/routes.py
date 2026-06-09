"""Analysis blueprint routes — weak area dashboard."""

from flask import render_template, session

from app.analysis import analysis_bp
from app.analysis.weak_area_detector import get_ranked_weak_areas
from app.auth.helpers import login_required
from app.storage import load_session


@analysis_bp.route("/analysis")
@login_required
def dashboard():
    """Render the weak-area analysis dashboard for the current user."""
    email = session["email"]
    session_data = load_session(email)
    weak_areas = get_ranked_weak_areas(session_data)
    turn_count = len(session_data.get("turns", []))
    return render_template(
        "analysis/dashboard.html",
        weak_areas=weak_areas,
        turn_count=turn_count,
    )
