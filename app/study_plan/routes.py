"""Study plan blueprint routes."""

import json
import logging
from datetime import date
from threading import Thread

logger = logging.getLogger(__name__)

import anthropic
from flask import Response, current_app, flash, make_response, redirect, render_template, request, session, stream_with_context, url_for

from app.analysis.weak_area_detector import get_daily_focus, get_ranked_weak_areas
from app.auth.helpers import force_logout_redirect, get_current_user, login_required
from app.email_service import send_plan_email
from app.extensions import limiter
from app.social.missions import advance_missions, get_or_refresh_missions
from app.social.xp_engine import ensure_social_fields
from app.storage import StorageCorruptError, load_session, load_user, save_user
from app.study_plan import study_plan_bp
from app.study_plan.calendar_builder import build_ics
from app.study_plan.plan_generator import generate_study_plan, stream_study_plan


def _exam_passed(exam_date_str: str | None) -> bool:
    """Return True if the stored exam date is today or in the past."""
    if not exam_date_str:
        return False
    try:
        exam = date.fromisoformat(exam_date_str)
        return exam <= date.today()
    except ValueError:
        return False


@study_plan_bp.route("/study-plan", methods=["GET"])
@login_required
def plan():
    """Render the study plan page (read-only GET)."""
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

    is_pro = user.get("tier") == "pro"

    try:
        user = ensure_social_fields(user, email)
        user = get_or_refresh_missions(user, email)
        user, _ = advance_missions(user, "plan_today")
        save_user(email, user)
    except Exception as exc:
        logger.warning("Mission/social update failed on study plan visit for %s: %s", email, exc)

    daily_focus = get_daily_focus(session_data)
    return render_template(
        "study_plan/plan.html",
        weak_areas=weak_areas,
        generated_plan=stored_plan,
        target_date=stored_exam_date or user.get("target_exam_date"),
        fix_used=fix_used,
        has_plan=bool(stored_plan),
        daily_focus=daily_focus,
        is_pro=is_pro,
    )


@study_plan_bp.route("/study-plan/generate", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def generate():
    """Stream study plan generation as Server-Sent Events.

    Streams Claude's output token-by-token so the browser connection stays
    alive and the user sees progress. Saves the completed plan at the end.
    """
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        # Can't redirect inside a streaming response — send SSE error instead.
        def _auth_err():
            yield "event: error\ndata: Session expired. Please log in again.\n\n"
        return Response(stream_with_context(_auth_err()), content_type="text/event-stream")

    try:
        session_data = load_session(email)
    except StorageCorruptError:
        def _corrupt():
            yield "event: error\ndata: Session data corrupted. Please log in again.\n\n"
        return Response(stream_with_context(_corrupt()), content_type="text/event-stream")

    weak_areas = get_ranked_weak_areas(session_data)
    stored_plan = user.get("study_plan_content")
    fix_used = user.get("study_plan_fix_used", False)
    is_pro = user.get("tier") == "pro"
    target_date = request.form.get("target_date") or user.get("target_exam_date")
    is_fix = request.form.get("is_fix") == "1"

    # Enforce free-tier limits before starting the stream.
    if not is_pro:
        if stored_plan and fix_used:
            def _locked():
                yield "event: error\ndata: Your plan is locked. Upgrade to Pro for unlimited edits.\n\n"
            return Response(stream_with_context(_locked()), content_type="text/event-stream")
        if stored_plan and not fix_used and not is_fix:
            def _already():
                yield "event: error\ndata: You already have a plan. Use the date correction option, or upgrade to Pro.\n\n"
            return Response(stream_with_context(_already()), content_type="text/event-stream")

    def _event_stream():
        """Generator: stream Claude chunks, then save the completed plan."""
        chunks: list[str] = []
        try:
            for chunk in stream_study_plan(weak_areas, target_date):
                chunks.append(chunk)
                yield f"data: {json.dumps(chunk)}\n\n"
        except anthropic.APITimeoutError:
            logger.exception("API timeout streaming study plan for %s", email)
            yield "event: error\ndata: Plan generation timed out. Please try again.\n\n"
            return
        except anthropic.RateLimitError:
            logger.exception("Rate limit streaming study plan for %s", email)
            yield "event: error\ndata: The service is busy. Please wait a moment and try again.\n\n"
            return
        except anthropic.AuthenticationError:
            logger.exception("Auth error streaming study plan for %s", email)
            yield "event: error\ndata: Study plan generation is unavailable. Please contact support.\n\n"
            return
        except anthropic.APIError:
            logger.exception("API error streaming study plan for %s", email)
            yield "event: error\ndata: Could not generate your study plan. Please try again.\n\n"
            return

        # Save the completed plan using a fresh disk read so we never
        # overwrite fields written by a concurrent request.
        try:
            full_plan = "".join(chunks)
            fresh_user = load_user(email)
            if fresh_user is None:
                raise RuntimeError("User record not found when saving plan.")
            fresh_user["study_plan_content"] = full_plan
            fresh_user["study_plan_exam_date"] = target_date
            if not is_pro:
                fresh_user["study_plan_fix_used"] = bool(is_fix)
            save_user(email, fresh_user)
        except Exception as exc:
            logger.warning("Failed to save study plan for %s: %s", email, exc)
            yield "event: error\ndata: Plan was generated but could not be saved. Please try again.\n\n"
            return

        # Fire email in background so SMTP latency never blocks the response.
        _app = current_app._get_current_object()
        _plan = full_plan
        _date = target_date
        def _send():
            with _app.app_context():
                try:
                    send_plan_email(email, _plan, _date)
                except Exception as exc:
                    logger.warning("Plan email failed for %s: %s", email, exc)
        Thread(target=_send, daemon=True).start()

        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(_event_stream()),
        content_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",  # disable nginx buffering
            "Cache-Control": "no-cache",
        },
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
