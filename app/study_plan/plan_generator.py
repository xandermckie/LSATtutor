"""Generate a personalized LSAT study plan using Claude."""

import logging
import os
from collections.abc import Iterator

import anthropic

logger = logging.getLogger(__name__)

_plan_client: anthropic.Anthropic | None = None


def _get_plan_client() -> anthropic.Anthropic:
    """Return a shared Anthropic client for plan requests."""
    global _plan_client
    if _plan_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")
        # No hard read timeout — streaming keeps the connection alive.
        _plan_client = anthropic.Anthropic(
            api_key=api_key,
            timeout=anthropic.Timeout(connect=10.0, read=None, write=10.0, pool=5.0),
        )
    return _plan_client


def _build_prompt(weak_areas: list[tuple[str, int]], target_date: str | None) -> str:
    """Assemble the study plan prompt."""
    area_text = (
        "\n".join(f"- {qtype} ({count} errors)" for qtype, count in weak_areas)
        if weak_areas
        else "No specific weak areas identified yet."
    )
    date_text = f"Target exam date: {target_date}" if target_date else "No exam date set."
    return (
        f"Create a focused LSAT study plan for a student with these details:\n\n"
        f"{date_text}\n\nWeak areas:\n{area_text}\n\n"
        "Produce a week-by-week plan (up to 8 weeks) with specific daily focus areas, "
        "practice targets, and review checkpoints. For each week include: a theme, "
        "Monday–Sunday daily tasks (30–90 min each), a mid-week check-in goal, and a "
        "weekend review exercise. Format as markdown with week headers."
    )


def stream_study_plan(weak_areas: list[tuple[str, int]], target_date: str | None) -> Iterator[str]:
    """Yield text chunks from Claude as the study plan is generated.

    Raises anthropic API exceptions on hard failures so callers can handle them.
    """
    prompt = _build_prompt(weak_areas, target_date)
    client = _get_plan_client()
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        yield from stream.text_stream


def generate_study_plan(weak_areas: list[tuple[str, int]], target_date: str | None) -> str:
    """Call Claude to produce a week-by-week study plan (non-streaming fallback).

    Returns a markdown string, or a user-friendly error message.
    """
    try:
        return "".join(stream_study_plan(weak_areas, target_date))
    except anthropic.APITimeoutError:
        logger.exception("Claude API timeout in generate_study_plan")
        return "Plan generation timed out. Please try again — it sometimes takes a moment for longer plans."
    except anthropic.APIConnectionError:
        logger.exception("Claude API connection error in generate_study_plan")
        return "Could not reach the tutoring service. Please check your connection and try again."
    except anthropic.RateLimitError:
        logger.exception("Claude API rate limit error in generate_study_plan")
        return "The service is busy right now. Please wait a moment and try generating your plan again."
    except anthropic.AuthenticationError:
        logger.exception("Claude API authentication error in generate_study_plan")
        return "Study plan generation is unavailable. Please contact support."
    except anthropic.APIError:
        logger.exception("Unexpected Claude API error in generate_study_plan")
        return "Could not generate your study plan. Please try again in a few minutes."
