"""Outbound email helpers — all mail goes through Flask-Mail."""

from flask import current_app
from flask_mail import Message

from app.extensions import mail


def send_daily_reminder(user_email: str, focus_area: str, exam_date: str | None) -> bool:
    """Send a short daily study nudge email.

    Does nothing and returns False silently when mail is not configured.

    Args:
        user_email: Recipient address.
        focus_area: Today's recommended focus question type.
        exam_date: ISO date string for the target exam, or None.

    Returns:
        True if the email was sent, False otherwise.
    """
    if not current_app.config.get("MAIL_ENABLED"):
        return False
    if not current_app.config.get("MAIL_PASSWORD"):
        return False

    exam_line = f"Your exam is on {exam_date}. Keep pushing!" if exam_date else "Set your exam date in Study Plan to get a personalized schedule."
    body = (
        "Hi,\n\n"
        f"Today's focus: {focus_area}\n\n"
        f"{exam_line}\n\n"
        "Head to the Tutor Chat to practice, or take a quick quiz to sharpen your skills.\n\n"
        "Good luck today!\n"
        "The Ratio Team\n"
    )

    try:
        msg = Message(
            subject=f"Ratio: Today focus on {focus_area}",
            recipients=[user_email],
            body=body,
        )
        mail.send(msg)
        return True
    except Exception:
        return False


def send_plan_email(user_email: str, plan_text: str, exam_date: str | None) -> bool:
    """Send the user's study plan to their email address.

    Does nothing and returns False silently if MAIL_ENABLED is False or
    if MAIL_PASSWORD is not configured, so a missing mail setup never
    crashes the plan generation flow.

    Args:
        user_email: Recipient address.
        plan_text: The raw markdown plan text.
        exam_date: ISO date string for the target exam, or None.

    Returns:
        True if the email was sent, False otherwise.
    """
    if not current_app.config.get("MAIL_ENABLED"):
        return False
    if not current_app.config.get("MAIL_PASSWORD"):
        return False

    exam_line = f"Target exam date: {exam_date}" if exam_date else "No exam date set."
    body = (
        "Hi,\n\n"
        "Here is your personalized LSAT study plan from Ratio.\n\n"
        f"{exam_line}\n\n"
        "--- YOUR STUDY PLAN ---\n\n"
        f"{plan_text}\n\n"
        "---\n\n"
        "Log in at any time to view your plan, track weak areas, and practice.\n\n"
        "Good luck on your LSAT!\n"
        "The Ratio Team\n"
        "contact.ratio.tutor@gmail.com\n"
    )

    try:
        msg = Message(
            subject="Your Ratio LSAT Study Plan",
            recipients=[user_email],
            body=body,
        )
        mail.send(msg)
        return True
    except Exception:
        return False
