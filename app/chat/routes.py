"""Chat blueprint routes — the main tutoring interface."""

from flask import current_app, jsonify, redirect, render_template, request, session, url_for

from app.auth.helpers import login_required
from app.chat import chat_bp
from app.chat.claude_client import call_claude
from app.chat.context_manager import maybe_compress
from app.chat.prompt_builder import build_messages
from app.extensions import limiter
from app.storage import load_session, save_session


@chat_bp.route("/chat", methods=["GET"])
@login_required
def chat():
    """Render the main chat interface."""
    return render_template("chat/chat.html")


@chat_bp.route("/chat", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def send_message():
    """Accept a student's message, call Claude, and return the coaching response.

    Expects JSON body: {"message": "..."}
    Returns JSON: {"response": "..."}
    """
    data = request.get_json(silent=True)
    if not data or not data.get("message", "").strip():
        return jsonify({"error": "Message is required."}), 400

    email = session["email"]
    user_input = data["message"].strip()

    session_data = load_session(email)
    session_data = maybe_compress(
        session_data,
        threshold=current_app.config["CONTEXT_COMPRESSION_THRESHOLD"],
        turns_to_compress=current_app.config["CONTEXT_TURNS_TO_COMPRESS"],
    )

    messages, system = build_messages(
        user_input=user_input,
        turns=session_data.get("turns", []),
        summary=session_data.get("summary", ""),
        weak_areas=session_data.get("weak_areas", {}),
    )

    response_text = call_claude(
        messages=messages,
        system=system,
        cache_dir=current_app.config["CACHE_DIR"],
    )

    session_data.setdefault("turns", []).append({"role": "user", "content": user_input})
    session_data["turns"].append({"role": "assistant", "content": response_text})
    save_session(email, session_data)

    return jsonify({"response": response_text})


@chat_bp.route("/history")
@login_required
def history():
    """Return the current user's chat history as JSON."""
    email = session["email"]
    session_data = load_session(email)
    return jsonify({"turns": session_data.get("turns", [])})


@chat_bp.route("/clear-history", methods=["POST"])
@login_required
def clear_history():
    """Clear all session history for the current user."""
    email = session["email"]
    save_session(email, {"turns": [], "summary": "", "weak_areas": {}})
    return redirect(url_for("chat.chat"))
