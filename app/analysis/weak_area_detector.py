"""Detect and rank a student's weak areas from session history."""

import re

QUESTION_TYPE_KEYWORDS = {
    "Strengthen": ["strengthen", "most strengthens", "supports the argument"],
    "Weaken": ["weaken", "most weakens", "undermines", "calls into question"],
    "Assumption": ["assumption", "assumes", "presupposes", "relies on the assumption"],
    "Flaw": ["flaw", "error in reasoning", "vulnerable to criticism", "reasoning is flawed"],
    "Inference": ["inference", "must be true", "can be concluded", "follows from"],
    "Main Point": ["main point", "main conclusion", "best expresses the conclusion"],
    "Parallel Reasoning": ["parallel", "most similar in its reasoning"],
    "Principle": ["principle", "most closely conforms", "illustrates"],
    "Resolve": ["resolve", "reconcile", "explain", "discrepancy"],
    "Analytical Reasoning": ["game", "schedule", "order", "arrangement", "if", "then", "exactly"],
    "Reading Comprehension": ["passage", "author", "according to the passage"],
}


def detect_question_type(text: str) -> str | None:
    """Guess the LSAT question type from a text string using keyword matching.

    Args:
        text: A question or student message to classify.

    Returns:
        The matched question type string, or None if no match.
    """
    lower = text.lower()
    for qtype, keywords in QUESTION_TYPE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return qtype
    return None


def update_weak_areas(
    session_data: dict,
    user_message: str,
    was_correct: bool,
    question_type: str | None = None,
) -> dict:
    """Update the weak_areas tally in session_data based on a user interaction.

    Increments the error count for the detected question type if the answer was wrong.

    Args:
        session_data: The full session dict.
        user_message: The student's most recent message (used for keyword detection fallback).
        was_correct: Whether their answer was correct.
        question_type: If already known, skip keyword detection and use this directly.

    Returns:
        The updated session_data dict.
    """
    if was_correct:
        return session_data

    qtype = question_type or detect_question_type(user_message)
    if qtype:
        weak = session_data.setdefault("weak_areas", {})
        weak[qtype] = weak.get(qtype, 0) + 1

    return session_data


_DEFAULT_TIPS = [
    "Assumption questions",
    "Weaken questions",
    "Strengthen questions",
    "Flaw questions",
    "Inference questions",
    "Main Point questions",
    "Parallel Reasoning questions",
    "Principle questions",
    "Resolve questions",
    "Analytical Reasoning (Logic Games)",
    "Reading Comprehension",
]


def get_daily_focus(session_data: dict) -> str:
    """Return the question type the student should focus on today.

    Uses the top weak area if any exist; otherwise rotates through a default
    tip list based on the calendar day so it changes daily.

    Args:
        session_data: The full session dict.

    Returns:
        A short focus label string, e.g. "Assumption questions".
    """
    from datetime import date

    weak = session_data.get("weak_areas", {})
    if weak:
        top = max(weak, key=lambda k: weak[k])
        return top
    day_index = date.today().toordinal() % len(_DEFAULT_TIPS)
    return _DEFAULT_TIPS[day_index]


def get_ranked_weak_areas(session_data: dict) -> list[tuple[str, int]]:
    """Return weak areas sorted by error count, highest first.

    Args:
        session_data: The full session dict.

    Returns:
        List of (question_type, error_count) tuples.
    """
    weak = session_data.get("weak_areas", {})
    return sorted(weak.items(), key=lambda x: x[1], reverse=True)
