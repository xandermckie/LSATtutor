"""Profile blueprint routes — avatar, username, password, export, delete."""

import csv
import hashlib
import io
import os
from datetime import datetime, timezone

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from app.auth.helpers import (
    force_logout_redirect,
    get_current_user,
    get_current_user_for_api,
    hash_password,
    login_required,
    verify_password,
)
from app.extensions import limiter
from app.profile import profile_bp
from app.storage import (
    StorageCorruptError,
    delete_session,
    delete_user,
    load_session,
    save_user,
)

_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
_MAGIC_BYTES = {
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}


def _avatar_path(email: str, avatars_dir: str) -> str:
    """Return the filesystem path for a user's avatar file.

    Args:
        email: The user's email address.
        avatars_dir: The directory where avatars are stored.

    Returns:
        Absolute path string for this user's avatar.
    """
    hashed = hashlib.sha256(email.lower().encode()).hexdigest()
    return os.path.join(avatars_dir, f"{hashed}.jpg")


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def profile():
    """Render the profile page and handle username changes on POST."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp

    if request.method == "POST":
        raw = request.form.get("username", "").strip()
        username = raw[:50].replace("<", "").replace(">", "").replace("&", "")
        if username:
            user["username"] = username
            save_user(email, user)
            flash("Username updated.", "success")
        return redirect(url_for("profile.profile"))

    avatar_exists = os.path.isfile(
        _avatar_path(email, current_app.config["AVATARS_DIR"])
    )
    return render_template(
        "profile/profile.html",
        username=user.get("username", ""),
        email=email,
        agreed_at=user.get("agreed_to_terms_at"),
        avatar_exists=avatar_exists,
    )


@profile_bp.route("/avatar/upload", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def upload_avatar():
    """Accept a profile picture upload (PNG or JPEG, max 2 MB).

    Validates file extension, size, and magic bytes before saving.
    """
    email = session["email"]
    file = request.files.get("avatar")

    if not file or not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for("profile.profile"))

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        flash("Only PNG and JPEG images are accepted.", "error")
        return redirect(url_for("profile.profile"))

    data = file.read()
    if len(data) > current_app.config["MAX_AVATAR_BYTES"]:
        flash("Image must be 2 MB or smaller.", "error")
        return redirect(url_for("profile.profile"))

    valid_magic = any(data.startswith(magic) for magic in _MAGIC_BYTES)
    if not valid_magic:
        flash("File does not appear to be a valid PNG or JPEG image.", "error")
        return redirect(url_for("profile.profile"))

    path = _avatar_path(email, current_app.config["AVATARS_DIR"])
    with open(path, "wb") as f:
        f.write(data)

    flash("Profile picture updated.", "success")
    return redirect(url_for("profile.profile"))


@profile_bp.route("/avatar")
@login_required
def avatar():
    """Serve the current user's avatar image, or the default placeholder."""
    email = session["email"]
    path = _avatar_path(email, current_app.config["AVATARS_DIR"])

    if os.path.isfile(path):
        return send_file(path, mimetype="image/jpeg")

    default = os.path.join(current_app.root_path, "static", "default_avatar.png")
    return send_file(default, mimetype="image/png")


@profile_bp.route("/password", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def change_password():
    """Update the user's password after verifying the old one.

    Requires: old_password, new_password, confirm_password form fields.
    """
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp

    old_pw = request.form.get("old_password", "")
    new_pw = request.form.get("new_password", "")
    confirm_pw = request.form.get("confirm_password", "")

    stored_hash = user.get("password_hash")
    if not stored_hash:
        flash("Cannot update password — account data error. Please contact support.", "error")
        return redirect(url_for("profile.profile"))

    if not verify_password(old_pw, stored_hash):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile.profile"))

    if len(new_pw) < 8:
        flash("New password must be at least 8 characters.", "error")
        return redirect(url_for("profile.profile"))

    if new_pw != confirm_pw:
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile.profile"))

    if new_pw == old_pw:
        flash("New password must differ from the current password.", "error")
        return redirect(url_for("profile.profile"))

    user["password_hash"] = hash_password(new_pw)
    save_user(email, user)
    flash("Password updated successfully.", "success")
    return redirect(url_for("profile.profile"))


@profile_bp.route("/export")
@login_required
def export():
    """Download the user's data as a CSV file.

    Includes chat history, weak area tallies, and study plan metadata.
    """
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp
    try:
        session_data = load_session(email)
    except StorageCorruptError:
        return force_logout_redirect()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["--- Chat History ---"])
    writer.writerow(["turn_index", "role", "content"])
    for i, turn in enumerate(session_data.get("turns", [])):
        writer.writerow([i, turn.get("role", ""), turn.get("content", "")])

    writer.writerow([])
    writer.writerow(["--- Weak Areas ---"])
    writer.writerow(["question_type", "miss_count"])
    weak = session_data.get("weak_areas", {})
    if isinstance(weak, dict):
        for qtype, count in sorted(weak.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([qtype, count])

    writer.writerow([])
    writer.writerow(["--- Study Plan ---"])
    writer.writerow(["field", "value"])
    writer.writerow(["target_exam_date", user.get("target_exam_date", "")])
    writer.writerow(["study_plan_exam_date", user.get("study_plan_exam_date", "")])

    buf = io.BytesIO(output.getvalue().encode("utf-8"))
    buf.seek(0)
    return send_file(
        buf,
        mimetype="text/csv",
        as_attachment=True,
        download_name="lsat_tutor_data.csv",
    )


@profile_bp.route("/pomodoro-intro/dismiss", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def dismiss_pomodoro_intro():
    """Record that the user dismissed the Pomodoro timer intro popup."""
    email = session["email"]
    user, error_resp = get_current_user_for_api()
    if error_resp:
        return error_resp
    if not user.get("pomodoro_intro_dismissed_at"):
        user["pomodoro_intro_dismissed_at"] = datetime.now(timezone.utc).isoformat()
        save_user(email, user)
    return jsonify({"ok": True})


@profile_bp.route("/delete", methods=["POST"])
@login_required
@limiter.limit("3 per hour")
def delete_account():
    """Permanently delete the account, session, and avatar after confirmation.

    Requires the user to type DELETE in the confirmation field.
    """
    confirm_text = request.form.get("confirm_text", "").strip()
    if confirm_text != "DELETE":
        flash("To delete your account, type DELETE exactly in the confirmation box.", "error")
        return redirect(url_for("profile.profile"))

    email = session["email"]

    avatar_path = _avatar_path(email, current_app.config["AVATARS_DIR"])
    if os.path.isfile(avatar_path):
        os.remove(avatar_path)

    delete_session(email)
    delete_user(email)
    session.clear()

    flash("Your account and all associated data have been permanently deleted.", "info")
    return redirect(url_for("auth.login"))
