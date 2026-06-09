"""Tests for prompt building and context manager."""

import pytest
from app.chat.prompt_builder import build_messages
from app.chat.context_manager import maybe_compress


def test_build_messages_includes_user_input():
    """The last message in the list is the student's input."""
    messages, system = build_messages(
        user_input="What is a weaken question?",
        turns=[],
        summary="",
        weak_areas={},
    )
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "What is a weaken question?"


def test_build_messages_injects_weak_areas():
    """Weak areas appear in the system prompt."""
    _, system = build_messages(
        user_input="test",
        turns=[],
        summary="",
        weak_areas={"Weaken": 5},
    )
    assert "Weaken" in system


def test_build_messages_with_summary():
    """A non-empty summary produces two extra prefix messages."""
    messages, _ = build_messages(
        user_input="test",
        turns=[],
        summary="Earlier we covered weaken questions.",
        weak_areas={},
    )
    assert any("summary" in m["content"].lower() for m in messages)


def test_maybe_compress_no_op_below_threshold():
    """maybe_compress is a no-op when turns are below the threshold."""
    session_data = {
        "turns": [{"role": "user", "content": f"msg {i}"} for i in range(5)],
        "summary": "",
        "weak_areas": {},
    }
    result = maybe_compress(session_data, threshold=10, turns_to_compress=5)
    assert len(result["turns"]) == 5


def test_maybe_compress_reduces_turns(monkeypatch):
    """maybe_compress removes old turns and stores a summary when over threshold."""
    def fake_compress(turns, existing):
        return "compressed summary"

    import app.chat.context_manager as cm
    monkeypatch.setattr(cm, "_compress_turns", fake_compress)

    session_data = {
        "turns": [{"role": "user", "content": f"msg {i}"} for i in range(12)],
        "summary": "",
        "weak_areas": {},
    }
    result = maybe_compress(session_data, threshold=10, turns_to_compress=5)
    assert len(result["turns"]) == 7
    assert result["summary"] == "compressed summary"
