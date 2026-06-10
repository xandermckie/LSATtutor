"""Study plan blueprint routes."""

from datetime import date

from flask import flash, make_response, redirect, render_template, request, session, url_for

from app.analysis.weak_area_detector import get_daily_focus, get_ranked_weak_areas
from app.auth.helpers import force_logout_redirect, get_current_user, login_required
from app.email_service import send_plan_email
from app.extensions import limiter
from app.storage import StorageCorruptError, load_session, save_user
from app.study_plan import study_plan_bp
from app.study_plan.calendar_builder import build_ics
from app.study_plan.plan_generator import generate_study_plan


def _exam_passed(exam_date_str: str | None) -> bool:
    """Return True if the stored exam date is today or in the past."""
    if not exam_date_str:
        return False
    try:
        exam = date.fromisoformat(exam_date_str)
        return exam <= date.today()
    except ValueError:
        return False


@study_plan_bp.route("/study-plan", methods=["GET", "POST"])
@login_required
def plan():
    """Render or generate a personalized study plan.

    Users get one plan generation and one free date correction.
    After both are used the plan is locked until the exam date passes.
    """
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp
    try:
        session_data = load_session(email)
    except StorageCorruptError:
        return force_logout_redirect()
    weak_areas = get_ranked_weak_areas(session_data)

    stored_plan = user.get("study_plan_content")
    fix_used = user.get("study_plan_fix_used", False)
    stored_exam_date = user.get("study_plan_exam_date")
    plan_expired = _exam_passed(stored_exam_date)

    # Reset if exam date has passed so they can generate a fresh plan.
    if plan_expired and stored_plan:
        user["study_plan_content"] = None
        user["study_plan_fix_used"] = False
        user["study_plan_exam_date"] = None
        save_user(email, user)
        stored_plan = None
        fix_used = False
        stored_exam_date = None

    if request.method == "POST":
        target_date = request.form.get("target_date") or user.get("target_exam_date")
        is_fix = request.form.get("is_fix") == "1"

        if stored_plan and fix_used:
            flash("You have already used your one plan correction. Your plan is locked until your exam date passes.")
            return redirect(url_for("study_plan.plan"))

        if stored_plan and not fix_used and not is_fix:
            flash("You have already generated a plan. Use the date correction option if needed.")
            return redirect(url_for("study_plan.plan"))

        generated = generate_study_plan(weak_areas, target_date)
        user["study_plan_content"] = generated
        user["study_plan_exam_date"] = target_date
        if is_fix:
            user["study_plan_fix_used"] = True
        else:
            user["study_plan_fix_used"] = False
        save_user(email, user)

        send_plan_email(email, generated, target_date)

        return redirect(url_for("study_plan.plan"))

    daily_focus = get_daily_focus(session_data)
    return render_template(
        "study_plan/plan.html",
        weak_areas=weak_areas,
        generated_plan=stored_plan,
        target_date=stored_exam_date or user.get("target_exam_date"),
        fix_used=fix_used,
        has_plan=bool(stored_plan),
        daily_focus=daily_focus,
    )


@study_plan_bp.route("/study-plan/export.ics", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def export_ics():
    """Generate and download a .ics calendar file for the user's study schedule."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp
    try:
        session_data = load_session(email)
    except StorageCorruptError:
        return force_logout_redirect()
    weak_areas = get_ranked_weak_areas(session_data)

    exam_date = user.get("study_plan_exam_date") or user.get("target_exam_date")

    selected_days = request.form.getlist("days")
    start_time = request.form.get("start_time", "19:00")
    raw_duration = request.form.get("duration", "60").strip()
    try:
        duration = int(raw_duration)
    except ValueError:
        flash("Session duration must be a whole number of minutes.", "error")
        return redirect(url_for("study_plan.plan"))
    if duration <= 0 or duration > 480:
        flash("Session duration must be between 1 and 480 minutes.", "error")
        return redirect(url_for("study_plan.plan"))

    ics_bytes = build_ics(exam_date, weak_areas, selected_days, start_time, duration)

    response = make_response(ics_bytes)
    response.headers["Content-Type"] = "text/calendar; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=ratio_study_plan.ics"
    return response


@study_plan_bp.route("/study-plan/send-reminder", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def send_reminder():
    """Re-send the stored study plan to the user's email address."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp
    plan_text = user.get("study_plan_content")
    exam_date = user.get("study_plan_exam_date")

    if not plan_text:
        flash("You do not have a study plan yet. Generate one first.")
        return redirect(url_for("study_plan.plan"))

    sent = send_plan_email(email, plan_text, exam_date)
    if sent:
        flash("Study plan sent to your email.")
    else:
        flash("Email is not configured. Ask the site admin to set up MAIL_PASSWORD in the environment.")
    return redirect(url_for("study_plan.plan"))
