"""Manages session context compression to keep the Claude context window bounded."""

import os

import anthropic

COMPRESSION_SYSTEM = (
    "You are a study session summarizer. "
    "Compress the following LSAT tutoring conversation turns into a 2-3 sentence summary "
    "that captures the question types covered, any patterns the student struggled with, "
    "and key coaching points given. Be concise — this summary will be prepended to future sessions."
)


def maybe_compress(session_data: dict, threshold: int, turns_to_compress: int) -> dict:
    """Compress old session turns if the turn count exceeds the threshold.

    Args:
        session_data: The full session dict with keys 'turns', 'summary', 'weak_areas'.
        threshold: Compress when len(turns) exceeds this value.
        turns_to_compress: How many of the oldest turns to compress into the summary.

    Returns:
        The (possibly updated) session dict.
    """
    turns = session_data.get("turns", [])
    if len(turns) <= threshold:
        return session_data

    old_turns = turns[:turns_to_compress]
    remaining = turns[turns_to_compress:]

    new_summary = _compress_turns(old_turns, session_data.get("summary", ""))
    session_data["summary"] = new_summary
    session_data["turns"] = remaining
    return session_data


def _compress_turns(turns: list[dict], existing_summary: str) -> str:
    """Call Claude to summarize a list of turns into a short string.

    Falls back to a truncated plain-text join on API error.

    Args:
        turns: List of {"role": ..., "content": ...} dicts to compress.
        existing_summary: Any prior summary to fold into the new one.

    Returns:
        A short summary string.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _plain_fallback(turns, existing_summary)

    content_lines = []
    if existing_summary:
        content_lines.append(f"Prior summary: {existing_summary}\n")
    for t in turns:
        content_lines.append(f"{t['role'].upper()}: {t['content']}")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=COMPRESSION_SYSTEM,
            messages=[{"role": "user", "content": "\n".join(content_lines)}],
        )
        return response.content[0].text.strip()
    except anthropic.APIError:
        return _plain_fallback(turns, existing_summary)


def _plain_fallback(turns: list[dict], existing_summary: str) -> str:
    """Build a minimal summary without calling the API."""
    base = existing_summary + " " if existing_summary else ""
    snippet = " | ".join(
        t["content"][:80] for t in turns if t["role"] == "user"
    )
    return (base + "Topics covered: " + snippet)[:500]
