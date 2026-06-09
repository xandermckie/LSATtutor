"""Generate a personalized LSAT study plan using Claude."""

import os

import anthropic


def generate_study_plan(weak_areas: list[tuple[str, int]], target_date: str | None) -> str:
    """Call Claude to produce a week-by-week study plan.

    Args:
        weak_areas: Ranked list of (question_type, error_count) tuples.
        target_date: The student's exam date string (e.g. "2025-09-13"), or None.

    Returns:
        A markdown-formatted study plan string, or a fallback message on error.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Study plan generation is unavailable — API key not configured."

    area_text = (
        "\n".join(f"- {qtype} ({count} errors)" for qtype, count in weak_areas)
        if weak_areas
        else "No specific weak areas identified yet."
    )
    date_text = f"Target exam date: {target_date}" if target_date else "No exam date set."

    prompt = (
        f"Create a focused LSAT study plan for a student with these details:\n\n"
        f"{date_text}\n\nWeak areas:\n{area_text}\n\n"
        "Produce a week-by-week plan (up to 8 weeks) with specific daily focus areas, "
        "practice targets, and review checkpoints. Format as markdown with week headers."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except anthropic.APIError as e:
        return f"Could not generate study plan at this time. Please try again later. ({e})"
