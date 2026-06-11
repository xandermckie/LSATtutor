"""Daily mission generation and progress tracking."""

import random
from datetime import date

from app.social.xp_engine import award_xp

# Pool of all possible daily missions.
MISSION_POOL = [
    {"id": "answer_3",    "label": "Answer 3 questions",                  "goal": 3,  "xp": 30, "tracks": "questions_today",  "icon": "quiz"},
    {"id": "answer_5",    "label": "Answer 5 questions",                  "goal": 5,  "xp": 40, "tracks": "questions_today",  "icon": "quiz"},
    {"id": "correct_3",   "label": "Get 3 correct answers",               "goal": 3,  "xp": 35, "tracks": "correct_today",    "icon": "check"},
    {"id": "correct_5",   "label": "Get 5 correct answers",               "goal": 5,  "xp": 50, "tracks": "correct_today",    "icon": "check"},
    {"id": "chat_tutor",  "label": "Send a message to the tutor",         "goal": 1,  "xp": 25, "tracks": "chat_today",       "icon": "chat"},
    {"id": "weaken_q",    "label": "Answer a Weaken question",            "goal": 1,  "xp": 20, "tracks": "weaken_today",     "icon": "logic"},
    {"id": "assumption_q","label": "Answer an Assumption question",       "goal": 1,  "xp": 20, "tracks": "assumption_today", "icon": "logic"},
    {"id": "rc_q",        "label": "Answer a Reading Comprehension question", "goal": 1, "xp": 20, "tracks": "rc_today",    "icon": "book"},
    {"id": "study_plan",  "label": "Visit your study plan",               "goal": 1,  "xp": 15, "tracks": "plan_today",       "icon": "calendar"},
    {"id": "streak_keep", "label": "Keep your streak alive today",        "goal": 1,  "xp": 20, "tracks": "streak_today",     "icon": "fire"},
    {"id": "chat_3",      "label": "Send 3 messages to the tutor",        "goal": 3,  "xp": 40, "tracks": "chat_today",       "icon": "chat"},
    {"id": "flaw_q",      "label": "Answer a Flaw question",              "goal": 1,  "xp": 20, "tracks": "flaw_today",       "icon": "logic"},
]

DAILY_COUNT = 3


def _pick_missions(seed: str) -> list[dict]:
    """Deterministically select DAILY_COUNT missions for today using a seed."""
    rng = random.Random(seed)
    return rng.sample(MISSION_POOL, DAILY_COUNT)


def get_or_refresh_missions(user: dict, email: str) -> dict:
    """Return today's missions, regenerating if the stored date is stale.

    Args:
        user: The user record dict (mutated in place when refreshed).
        email: Used as part of the per-user daily seed.

    Returns:
        The (possibly updated) user dict.
    """
    today = date.today().isoformat()
    if user.get("missions_date") == today:
        return user

    seed = f"{today}:{email}"
    templates = _pick_missions(seed)
    user["missions_date"] = today
    user["missions"] = [
        {**t, "progress": 0, "completed": False}
        for t in templates
    ]
    # Streak mission is auto-completed if the user already logged in today.
    already_streaking = user.get("streak_last_date") == today
    user["daily_activity"] = {
        "questions_today": 0,
        "correct_today": 0,
        "chat_today": 0,
        "weaken_today": 0,
        "assumption_today": 0,
        "rc_today": 0,
        "plan_today": 0,
        "streak_today": 1 if already_streaking else 0,
        "flaw_today": 0,
    }
    if already_streaking:
        for m in user["missions"]:
            if m["tracks"] == "streak_today":
                m["progress"] = 1
                m["completed"] = True

    return user


def advance_missions(user: dict, track: str, amount: int = 1) -> tuple[dict, int]:
    """Advance mission progress for all missions tracking the given key.

    Args:
        user: The user record dict (mutated in place).
        track: The activity key (e.g. "questions_today", "correct_today").
        amount: How much to add to the activity counter.

    Returns:
        (updated_user, total_xp_awarded_for_completed_missions)
    """
    today = date.today().isoformat()
    if user.get("missions_date") != today:
        return user, 0

    activity = user.setdefault("daily_activity", {})
    activity[track] = activity.get(track, 0) + amount

    total_xp = 0
    for mission in user.get("missions", []):
        if mission["completed"] or mission["tracks"] != track:
            continue
        mission["progress"] = min(activity[track], mission["goal"])
        if mission["progress"] >= mission["goal"]:
            mission["completed"] = True
            total_xp += mission["xp"]
            user = award_xp(user, mission["xp"])

    return user, total_xp
