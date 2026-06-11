"""Social blueprint routes — leaderboard, friends, and challenges."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from flask import flash, redirect, render_template, request, session, url_for

from app.auth.helpers import get_current_user, login_required
from app.extensions import limiter
from app.social import social_bp
from app.social.xp_engine import level_progress
from app.storage import load_user, save_user
from app.storage.user_store import load_all_users


def _uid(email: str) -> str:
    """Return the canonical user_id for an email address."""
    return hashlib.sha256(email.lower().encode()).hexdigest()


def _find_by_uid(uid: str) -> tuple[str | None, dict | None]:
    """Scan all users to find one whose user_id matches uid.

    Returns:
        (email, user_dict) or (None, None).
    """
    for u in load_all_users():
        if u.get("user_id") == uid:
            return u.get("email"), u
    return None, None


def _find_by_username(username: str) -> tuple[str | None, dict | None]:
    """Scan all users for one whose username matches (case-insensitive).

    Returns:
        (email, user_dict) or (None, None).
    """
    lower = username.lower()
    for u in load_all_users():
        if (u.get("username") or "").lower() == lower:
            return u.get("email"), u
    return None, None


def _challenge_label(ctype: str) -> str:
    """Return a human-readable label for a challenge type."""
    return {"xp_race": "XP Race", "question_blitz": "Question Blitz", "accuracy": "Accuracy Duel"}.get(ctype, ctype)


def _resolve_challenge_status(ch: dict, user: dict, is_challenger: bool) -> dict:
    """Annotate a challenge dict with current progress and winner info.

    Args:
        ch: The raw challenge dict from the user record.
        user: The current user's record (to compute live deltas).
        is_challenger: True if the current user issued the challenge.

    Returns:
        An enriched dict with added display fields.
    """
    now = datetime.now(timezone.utc)
    end = datetime.fromisoformat(ch["end_at"])
    expired = end <= now

    ctype = ch["type"]
    if is_challenger:
        my_baseline_xp = ch.get("challenger_baseline_xp", 0)
        my_baseline_q = ch.get("challenger_baseline_q", 0)
        my_baseline_c = ch.get("challenger_baseline_correct", 0)
    else:
        my_baseline_xp = ch.get("challenged_baseline_xp", 0)
        my_baseline_q = ch.get("challenged_baseline_q", 0)
        my_baseline_c = ch.get("challenged_baseline_correct", 0)

    if ctype == "xp_race":
        my_score = user.get("xp", 0) - my_baseline_xp
        metric = "XP gained"
    elif ctype == "question_blitz":
        my_score = user.get("total_questions", 0) - my_baseline_q
        metric = "questions answered"
    else:
        answered = user.get("total_questions", 0) - my_baseline_q
        correct = user.get("total_correct", 0) - my_baseline_c
        my_score = round(100 * correct / answered) if answered else 0
        metric = "% correct"

    time_left = str(end - now).split(".")[0] if not expired else "Ended"

    return {
        **ch,
        "label": _challenge_label(ctype),
        "my_score": max(0, my_score),
        "metric": metric,
        "expired": expired,
        "time_left": time_left,
    }


@social_bp.route("/leaderboard")
@login_required
def leaderboard():
    """Show global XP leaderboard and a friends-only ranking."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp

    all_users = load_all_users()
    board = []
    for u in all_users:
        board.append({
            "username": u.get("username") or (u.get("email") or "?").split("@")[0],
            "xp": u.get("xp", 0),
            "level": u.get("level", 1),
            "league": u.get("league", "Bronze"),
            "streak": u.get("streak_count", 0),
            "user_id": u.get("user_id", ""),
        })
    board.sort(key=lambda x: x["xp"], reverse=True)

    my_uid = _uid(email)
    friend_ids = set(user.get("friends", []))

    global_top = board[:20]
    friend_board = [u for u in board if u["user_id"] in friend_ids or u["user_id"] == my_uid]
    my_rank = next((i + 1 for i, u in enumerate(board) if u["user_id"] == my_uid), None)

    return render_template(
        "social/leaderboard.html",
        global_top=global_top,
        friend_board=friend_board,
        my_rank=my_rank,
        my_uid=my_uid,
        user=user,
        xp_info=level_progress(user.get("xp", 0)),
    )


@social_bp.route("/friends")
@login_required
def friends():
    """Show the friends list, pending requests, and active challenges."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp

    all_users = load_all_users()
    uid_map = {u.get("user_id", ""): u for u in all_users}

    friend_profiles = []
    for fid in user.get("friends", []):
        u = uid_map.get(fid, {})
        if u:
            friend_profiles.append({
                "user_id": fid,
                "username": u.get("username") or (u.get("email") or "?").split("@")[0],
                "xp": u.get("xp", 0),
                "level": u.get("level", 1),
                "league": u.get("league", "Bronze"),
                "streak": u.get("streak_count", 0),
            })

    pending_profiles = []
    for fid in user.get("pending_requests", []):
        u = uid_map.get(fid, {})
        if u:
            pending_profiles.append({
                "user_id": fid,
                "username": u.get("username") or (u.get("email") or "?").split("@")[0],
            })

    my_uid = _uid(email)
    is_challenger_map = {ch["id"]: ch["from_id"] == my_uid for ch in user.get("challenges", [])}

    active_challenges = []
    for ch in user.get("challenges", []):
        if ch.get("status") == "declined":
            continue
        end = datetime.fromisoformat(ch["end_at"])
        now = datetime.now(timezone.utc)
        if end < now and ch.get("status") == "expired":
            continue

        is_challenger = is_challenger_map.get(ch["id"], True)
        other_uid = ch["to_id"] if is_challenger else ch["from_id"]
        other_u = uid_map.get(other_uid, {})
        enriched = _resolve_challenge_status(ch, user, is_challenger)
        enriched["other_username"] = other_u.get("username") or (other_u.get("email") or "?").split("@")[0]
        enriched["is_challenger"] = is_challenger
        active_challenges.append(enriched)

    return render_template(
        "social/friends.html",
        friends=friend_profiles,
        pending=pending_profiles,
        challenges=active_challenges,
        user=user,
    )


@social_bp.route("/friends/add", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def add_friend():
    """Send a friend request by username or email."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp

    query = request.form.get("query", "").strip()
    if not query:
        flash("Enter a username or email to search.", "error")
        return redirect(url_for("social.friends"))

    target_email = target_user = None
    if "@" in query:
        target_user = load_user(query.lower())
        if target_user:
            target_email = query.lower()
    if not target_user:
        target_email, target_user = _find_by_username(query)

    if not target_user:
        flash("No user found with that username or email.", "error")
        return redirect(url_for("social.friends"))

    my_uid = _uid(email)
    their_uid = target_user.get("user_id") or _uid(target_email)

    if their_uid == my_uid:
        flash("You cannot add yourself.", "error")
        return redirect(url_for("social.friends"))

    if their_uid in user.get("friends", []):
        flash("You are already friends with that user.", "info")
        return redirect(url_for("social.friends"))

    if their_uid in user.get("sent_requests", []):
        flash("Friend request already sent.", "info")
        return redirect(url_for("social.friends"))

    target_user.setdefault("pending_requests", [])
    if my_uid not in target_user["pending_requests"]:
        target_user["pending_requests"].append(my_uid)
    save_user(target_email, target_user)

    user.setdefault("sent_requests", [])
    if their_uid not in user["sent_requests"]:
        user["sent_requests"].append(their_uid)
    save_user(email, user)

    their_display = target_user.get("username") or (target_email or "?").split("@")[0]
    flash(f"Friend request sent to {their_display}.", "success")
    return redirect(url_for("social.friends"))


@social_bp.route("/friends/accept", methods=["POST"])
@login_required
def accept_friend():
    """Accept an incoming friend request and create the mutual friendship."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp

    their_uid = request.form.get("user_id", "").strip()
    if not their_uid or their_uid not in user.get("pending_requests", []):
        flash("No pending request from that user.", "error")
        return redirect(url_for("social.friends"))

    user["pending_requests"].remove(their_uid)
    user.setdefault("friends", [])
    if their_uid not in user["friends"]:
        user["friends"].append(their_uid)
    save_user(email, user)

    their_email, their_user = _find_by_uid(their_uid)
    if their_user and their_email:
        my_uid = _uid(email)
        their_user.setdefault("friends", [])
        if my_uid not in their_user["friends"]:
            their_user["friends"].append(my_uid)
        their_user.get("sent_requests", []).count(my_uid)  # read-only guard
        save_user(their_email, their_user)

    flash("Friend request accepted!", "success")
    return redirect(url_for("social.friends"))


@social_bp.route("/friends/decline", methods=["POST"])
@login_required
def decline_friend():
    """Decline an incoming friend request."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp

    their_uid = request.form.get("user_id", "").strip()
    pending = user.get("pending_requests", [])
    if their_uid in pending:
        pending.remove(their_uid)
        user["pending_requests"] = pending
        save_user(email, user)

    flash("Friend request declined.", "info")
    return redirect(url_for("social.friends"))


@social_bp.route("/friends/remove", methods=["POST"])
@login_required
def remove_friend():
    """Remove a friend from both users' friend lists."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp

    their_uid = request.form.get("user_id", "").strip()
    friends_list = user.get("friends", [])
    if their_uid in friends_list:
        friends_list.remove(their_uid)
        user["friends"] = friends_list
        save_user(email, user)

        their_email, their_user = _find_by_uid(their_uid)
        if their_user and their_email:
            my_uid = _uid(email)
            their_friends = their_user.get("friends", [])
            if my_uid in their_friends:
                their_friends.remove(my_uid)
                their_user["friends"] = their_friends
                save_user(their_email, their_user)

    flash("Friend removed.", "info")
    return redirect(url_for("social.friends"))


@social_bp.route("/challenges/send", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def send_challenge():
    """Issue a 24-hour challenge to a friend."""
    email = session["email"]
    user, redirect_resp = get_current_user()
    if redirect_resp:
        return redirect_resp

    their_uid = request.form.get("user_id", "").strip()
    ctype = request.form.get("type", "xp_race").strip()
    if ctype not in ("xp_race", "question_blitz", "accuracy"):
        flash("Unknown challenge type.", "error")
        return redirect(url_for("social.friends"))

    if their_uid not in user.get("friends", []):
        flash("You can only challenge friends.", "error")
        return redirect(url_for("social.friends"))

    their_email, their_user = _find_by_uid(their_uid)
    if not their_user:
        flash("Could not find that user.", "error")
        return redirect(url_for("social.friends"))

    now = datetime.now(timezone.utc)
    ch_id = str(uuid.uuid4())[:8]
    my_uid = _uid(email)

    ch_base = {
        "id": ch_id,
        "type": ctype,
        "from_id": my_uid,
        "to_id": their_uid,
        "status": "active",
        "start_at": now.isoformat(),
        "end_at": (now + timedelta(days=1)).isoformat(),
    }

    # Challenger's copy — records their own baselines
    ch_challenger = {
        **ch_base,
        "challenger_baseline_xp": user.get("xp", 0),
        "challenger_baseline_q": user.get("total_questions", 0),
        "challenger_baseline_correct": user.get("total_correct", 0),
    }
    user.setdefault("challenges", [])
    user["challenges"].append(ch_challenger)
    save_user(email, user)

    # Challenged's copy — records their own baselines
    ch_challenged = {
        **ch_base,
        "challenged_baseline_xp": their_user.get("xp", 0),
        "challenged_baseline_q": their_user.get("total_questions", 0),
        "challenged_baseline_correct": their_user.get("total_correct", 0),
    }
    their_user.setdefault("challenges", [])
    their_user["challenges"].append(ch_challenged)
    save_user(their_email, their_user)

    flash(f"{_challenge_label(ctype)} challenge sent! It runs for 24 hours.", "success")
    return redirect(url_for("social.friends"))
