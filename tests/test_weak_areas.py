"""Tests for weak area detection logic."""

import json
import os

import pytest

from app.analysis.weak_area_detector import (
    detect_question_type,
    get_ranked_weak_areas,
    update_weak_areas,
)


def test_detect_weaken():
    """Keyword 'weaken' maps to the Weaken question type."""
    assert detect_question_type("Which of the following most weakens the argument?") == "Weaken"


def test_detect_assumption():
    """Keyword 'assumption' maps to the Assumption question type."""
    assert detect_question_type("The argument above assumes which of the following?") == "Assumption"


def test_detect_unknown():
    """Unrecognized text returns None."""
    assert detect_question_type("What is the capital of France?") is None


def test_update_weak_areas_increments_on_error():
    """A wrong answer increments the error count for the detected question type."""
    session_data = {"turns": [], "summary": "", "weak_areas": {}}
    session_data = update_weak_areas(session_data, "Which most weakens the argument?", was_correct=False)
    assert session_data["weak_areas"].get("Weaken") == 1


def test_update_weak_areas_no_increment_on_correct():
    """A correct answer does not modify weak_areas."""
    session_data = {"turns": [], "summary": "", "weak_areas": {}}
    session_data = update_weak_areas(session_data, "Which most weakens the argument?", was_correct=True)
    assert session_data["weak_areas"] == {}


def test_get_ranked_weak_areas():
    """get_ranked_weak_areas returns entries sorted by error count descending."""
    session_data = {"weak_areas": {"Weaken": 3, "Assumption": 5, "Flaw": 1}}
    ranked = get_ranked_weak_areas(session_data)
    assert ranked[0] == ("Assumption", 5)
    assert ranked[-1] == ("Flaw", 1)


def test_fixture_loads():
    """The sample_session fixture is valid JSON."""
    path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_session.json")
    with open(path) as f:
        data = json.load(f)
    assert "turns" in data
    assert "weak_areas" in data
