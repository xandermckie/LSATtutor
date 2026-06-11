"""Quiz blueprint routes."""

from flask import jsonify, render_template, request, session

from app.analysis.weak_area_detector import update_weak_areas
from app.auth.helpers import login_required
from app.extensions import limiter
from app.quiz import quiz_bp
from app.quiz.quiz_engine import check_answer, get_question
from app.social.missions import advance_missions, get_or_refresh_missions
from app.social.xp_engine import award_xp, ensure_social_fields, update_streak
from app.storage import load_session, load_user, load_user_cached, save_session, save_user


@quiz_bp.route("/quiz")
@login_required
def quiz():
    """Render the quiz interface with a fresh question."""
    question = get_question()
    session["quiz_question"] = question
    return render_template("quiz/quiz.html", question=question)


@quiz_bp.route("/quiz", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def submit_answer():
    """Accept and evaluate the student's answer, then return results as JSON."""
    submitted = request.form.get("answer", "").strip().upper()
    question = session.get("quiz_question")

    if not question:
        return jsonify({"error": "No active question. Start a new quiz."}), 400
    if not submitted:
        return jsonify({"error": "An answer choice is required."}), 400

    result = check_answer(question, submitted)
    email = session["email"]

    # --- session (weak area) update ---
    session_data = load_session(email)
    session_data = update_weak_areas(
        session_data,
        question["stimulus"],
        result["is_correct"],
        question_type=question.get("type"),
    )
    save_session(email, session_data)

    # --- user record: XP, streak, missions ---
    user = load_user_cached(email)
    user = ensure_social_fields(user, email)

    # Streak update on first answer of the day
    user, _streak_bonus = update_streak(user)

    # XP for answering
    xp_gain = 15 if result["is_correct"] else 3
    user = award_xp(user, xp_gain)

    # Running totals for leaderboard / challenges
    user["total_questions"] = user.get("total_questions", 0) + 1
    if result["is_correct"]:
        user["total_correct"] = user.get("total_correct", 0) + 1

    # Refresh missions for today, then advance relevant tracks
    user = get_or_refresh_missions(user, email)
    user, _ = advance_missions(user, "questions_today")
    if result["is_correct"]:
        user, _ = advance_missions(user, "correct_today")
    # Advance streak mission if active streak
    if user.get("streak_count", 0) >= 1:
        user, _ = advance_missions(user, "streak_today")

    # Advance question-type-specific mission tracks
    qtype = question.get("type", "")
    type_track_map = {
        "Weaken": "weaken_today",
        "Assumption": "assumption_today",
        "Reading Comprehension": "rc_today",
        "Flaw": "flaw_today",
    }
    if qtype in type_track_map:
        user, _ = advance_missions(user, type_track_map[qtype])

    save_user(email, user)

    return render_template("quiz/quiz.html", question=question, result=result, xp_gain=xp_gain)
