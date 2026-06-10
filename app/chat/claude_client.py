"""Anthropic SDK wrapper — all Claude API calls go through here."""

import hashlib
import json
import logging
import os

import anthropic

from app.extensions import get_cache

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    """Return a shared Anthropic client, creating it on first call."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY environment variable is not set."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _cache_key(messages: list[dict], system: str) -> str:
    """Derive a stable cache key from the message content."""
    payload = json.dumps({"system": system, "messages": messages}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def call_claude(messages: list[dict], system: str, cache_dir: str) -> str:
    """Send messages to Claude and return the text response.

    Checks diskcache first; falls back to a canned tip on API failure.

    Args:
        messages: List of message dicts (role + content).
        system: The system prompt string.
        cache_dir: Path to the diskcache directory.

    Returns:
        Claude's response text (or a fallback string on API error).
    """
    cache = get_cache(cache_dir)
    key = _cache_key(messages, system)

    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        text = response.content[0].text
        cache.set(key, text, expire=86400)
        return text
    except anthropic.APIConnectionError:
        logger.exception("Claude API connection error in call_claude")
        return "Could not reach the tutoring service. Please check your connection and try again."
    except anthropic.RateLimitError:
        logger.exception("Claude API rate limit error in call_claude")
        return "The tutoring service is busy right now. Please wait a moment and try again."
    except anthropic.AuthenticationError:
        logger.exception("Claude API authentication error in call_claude")
        return "API authentication failed. Please contact support."
    except anthropic.APIError:
        logger.exception("Unexpected Claude API error in call_claude")
        return _fallback_response()


def _fallback_response() -> str:
    """Return a canned fallback tip when the API is unavailable."""
    fallback_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "static",
        "fallback_responses.json",
    )
    try:
        with open(fallback_path, "r") as f:
            fallbacks = json.load(f)
        return fallbacks.get("general", _default_fallback())
    except (OSError, json.JSONDecodeError):
        return _default_fallback()


def _default_fallback() -> str:
    """Return a minimal hardcoded fallback message."""
    return (
        "The tutoring service is temporarily unavailable. "
        "Here is a general LSAT tip: Always identify the conclusion of an argument first. "
        "Everything else — premises, background, context — supports or weakens that conclusion. "
        "Please try again in a few minutes."
    )
