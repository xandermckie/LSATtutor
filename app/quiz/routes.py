"""Quiz blueprint routes."""

from flask import jsonify, render_template, request, session

from app.analysis.weak_area_detector import update_weak_areas
from app.auth.helpers import login_required
from app.extensions import limiter
from app.quiz import quiz_bp
from app.quiz.quiz_engine import check_answer, get_question
from app.storage import load_session, save_session


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
    session_data = load_session(email)
    session_data = update_weak_areas(session_data, question["stimulus"], result["is_correct"])
    save_session(email, session_data)

    return render_template("quiz/quiz.html", question=question, result=result)
