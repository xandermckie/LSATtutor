"""Study plan blueprint routes."""

from flask import render_template, request, session

from app.analysis.weak_area_detector import get_ranked_weak_areas
from app.auth.helpers import login_required
from app.storage import load_session, load_user
from app.study_plan import study_plan_bp
from app.study_plan.plan_generator import generate_study_plan


@study_plan_bp.route("/study-plan", methods=["GET", "POST"])
@login_required
def plan():
    """Render or generate a personalized study plan."""
    email = session["email"]
    user = load_user(email)
    session_data = load_session(email)
    weak_areas = get_ranked_weak_areas(session_data)
    generated_plan = None

    if request.method == "POST":
        target_date = request.form.get("target_date") or user.get("target_exam_date")
        generated_plan = generate_study_plan(weak_areas, target_date)

    return render_template(
        "study_plan/plan.html",
        weak_areas=weak_areas,
        generated_plan=generated_plan,
        target_date=user.get("target_exam_date"),
    )
