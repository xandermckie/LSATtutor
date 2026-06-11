"""XP, level, and league calculations for Ratio's gamification layer."""

from datetime import date, timedelta

LEAGUE_THRESHOLDS = [
    ("Diamond", 3500),
    ("Platinum", 2000),
    ("Gold", 1000),
    ("Silver", 500),
    ("Bronze", 0),
]

XP_PER_LEVEL = 100


def level_from_xp(xp: int) -> int:
    """Return the current level for a given XP total."""
    return 1 + max(0, xp) // XP_PER_LEVEL


def league_from_xp(xp: int) -> str:
    """Return the league name for a given XP total."""
    for name, threshold in LEAGUE_THRESHOLDS:
        if xp >= threshold:
            return name
    return "Bronze"


def level_progress(xp: int) -> dict:
    """Return level progress info for the XP bar.

    Returns:
        Dict with level, progress (XP into current level), needed (XP for next level), pct.
    """
    level = level_from_xp(xp)
    current_floor = (level - 1) * XP_PER_LEVEL
    progress = xp - current_floor
    needed = XP_PER_LEVEL
    return {
        "level": level,
        "league": league_from_xp(xp),
        "progress": progress,
        "needed": needed,
        "pct": int(100 * progress / needed),
    }


def award_xp(user: dict, amount: int) -> dict:
    """Add XP to a user dict and recompute level and league in place.

    Args:
        user: The user record dict (mutated in place).
        amount: Non-negative XP to add.

    Returns:
        The updated user dict.
    """
    user["xp"] = user.get("xp", 0) + max(0, amount)
    user["level"] = level_from_xp(user["xp"])
    user["league"] = league_from_xp(user["xp"])
    return user


def update_streak(user: dict) -> tuple[dict, int]:
    """Advance the daily streak if the user hasn't already logged in today.

    Must be called at most once per day per user (guarded by streak_last_date).

    Returns:
        (updated_user, bonus_xp_awarded)
    """
    today = date.today().isoformat()
    last = user.get("streak_last_date")

    if last == today:
        return user, 0

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    streak = user.get("streak_count", 0)
    streak = streak + 1 if last == yesterday else 1

    user["streak_count"] = streak
    user["streak_last_date"] = today
    user["streak_longest"] = max(streak, user.get("streak_longest", 0))

    bonus = min(streak * 2, 20)
    user = award_xp(user, bonus)
    return user, bonus


def ensure_social_fields(user: dict, email: str) -> dict:
    """Back-fill social fields onto users created before this feature existed.

    Args:
        user: The user record dict (mutated in place if fields are missing).
        email: The user's email — used to derive user_id.

    Returns:
        The updated user dict.
    """
    import hashlib

    if not user.get("user_id"):
        user["user_id"] = hashlib.sha256(email.lower().encode()).hexdigest()
    user.setdefault("xp", 0)
    user.setdefault("level", 1)
    user.setdefault("league", "Bronze")
    user.setdefault("streak_count", 0)
    user.setdefault("streak_longest", 0)
    user.setdefault("streak_last_date", None)
    user.setdefault("total_questions", 0)
    user.setdefault("total_correct", 0)
    user.setdefault("friends", [])
    user.setdefault("pending_requests", [])
    user.setdefault("sent_requests", [])
    user.setdefault("challenges", [])
    user.setdefault("missions_date", None)
    user.setdefault("missions", [])
    user.setdefault("daily_activity", {})
    return user
