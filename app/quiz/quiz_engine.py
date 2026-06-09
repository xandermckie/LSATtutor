"""Quiz mode engine — selects questions, checks answers, records results."""

import os
import random

import anthropic

SAMPLE_QUESTIONS = [
    {
        "type": "Weaken",
        "stimulus": (
            "Studies show that students who attend tutoring sessions score higher on standardized tests. "
            "Therefore, tutoring causes higher test scores."
        ),
        "question": "Which of the following, if true, most weakens the argument above?",
        "choices": {
            "A": "Students who attend tutoring also tend to study more independently.",
            "B": "Tutoring sessions are expensive and not available to all students.",
            "C": "Some students who do not attend tutoring also score very high.",
            "D": "The studies were conducted across multiple countries.",
        },
        "correct": "A",
        "explanation": (
            "Choice A weakens the argument by introducing an alternative cause — "
            "the increased independent study, not the tutoring, could be driving the score gains."
        ),
    },
    {
        "type": "Assumption",
        "stimulus": (
            "The law school requires applicants to score in the 90th percentile on the LSAT. "
            "Maria scored in the 92nd percentile. Therefore, Maria will be admitted."
        ),
        "question": "The argument above assumes which of the following?",
        "choices": {
            "A": "Maria applied to only one law school.",
            "B": "The LSAT score is the only admission criterion.",
            "C": "Scoring above the 90th percentile guarantees admission.",
            "D": "Maria prepared extensively for the LSAT.",
        },
        "correct": "B",
        "explanation": (
            "The argument jumps from meeting one criterion (LSAT score) to being admitted. "
            "This only works if the LSAT score is the sole criterion — choice B."
        ),
    },
]


def get_question(question_type: str | None = None) -> dict:
    """Select a quiz question, optionally filtered by type.

    Args:
        question_type: If provided, only return questions of this type.

    Returns:
        A question dict with keys: type, stimulus, question, choices, correct, explanation.
    """
    pool = SAMPLE_QUESTIONS
    if question_type:
        pool = [q for q in SAMPLE_QUESTIONS if q["type"] == question_type] or SAMPLE_QUESTIONS
    return random.choice(pool)


def check_answer(question: dict, submitted: str) -> dict:
    """Evaluate a submitted answer choice against the correct answer.

    Args:
        question: The question dict as returned by get_question().
        submitted: The letter choice submitted by the student (e.g. "A").

    Returns:
        A dict with keys: is_correct (bool), correct (str), explanation (str).
    """
    is_correct = submitted.upper() == question["correct"]
    return {
        "is_correct": is_correct,
        "correct": question["correct"],
        "explanation": question["explanation"],
    }
