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


def update_weak_areas(session_data: dict, user_message: str, was_correct: bool) -> dict:
    """Update the weak_areas tally in session_data based on a user interaction.

    Increments the error count for the detected question type if the answer was wrong.

    Args:
        session_data: The full session dict.
        user_message: The student's most recent message.
        was_correct: Whether their answer was correct.

    Returns:
        The updated session_data dict.
    """
    if was_correct:
        return session_data

    qtype = detect_question_type(user_message)
    if qtype:
        weak = session_data.setdefault("weak_areas", {})
        weak[qtype] = weak.get(qtype, 0) + 1

    return session_data


def get_ranked_weak_areas(session_data: dict) -> list[tuple[str, int]]:
    """Return weak areas sorted by error count, highest first.

    Args:
        session_data: The full session dict.

    Returns:
        List of (question_type, error_count) tuples.
    """
    weak = session_data.get("weak_areas", {})
    return sorted(weak.items(), key=lambda x: x[1], reverse=True)
