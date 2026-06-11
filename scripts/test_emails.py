"""
Email template test script — renders every email template to HTML files so
you can preview them in a browser without needing a live mail server.

Usage:
    python scripts/test_emails.py

Output files land in  scripts/email_previews/  — open any .html file in
your browser to see exactly what the email will look like.

To test live delivery, set MAIL_ENABLED=true and MAIL_PASSWORD in .env,
then run:
    python scripts/test_emails.py --send your@email.com
"""

import argparse
import os
import sys

# Make sure the project root is importable
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

# Load .env before anything else so MAIL_PASSWORD etc. are available
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("APP_URL", "http://127.0.0.1:5000")

from cryptography.fernet import Fernet
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())

from app import create_app

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "email_previews")


def render_all(app, recipient: str | None = None) -> None:
    """Render every email template and either save to disk or send live.

    Args:
        app: The Flask application instance.
        recipient: If set, send live emails to this address (requires MAIL_ENABLED).
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with app.app_context():
        from flask import render_template

        templates = [
            (
                "welcome",
                "email/welcome.html",
                {
                    "display_name": "Alex",
                    "app_url": "http://127.0.0.1:5000",
                },
                "Welcome to Ratio — your LSAT tutor is ready",
            ),
            (
                "weekly_digest",
                "email/weekly_digest.html",
                {
                    "display_name": "Alex",
                    "app_url": "http://127.0.0.1:5000",
                    "week_of": "June 9, 2026",
                    "questions_this_week": 47,
                    "accuracy_pct": 72,
                    "xp_earned": 340,
                    "streak_count": 5,
                    "top_weak_area": "Weaken",
                    "weak_area_tip": (
                        "Find a premise that, if true, makes the conclusion less likely — "
                        "look for alternative causes or counter-evidence."
                    ),
                    "upcoming_exam_date": "2026-09-13",
                    "days_until_exam": 94,
                },
                "Your Ratio weekly update — week of June 9, 2026",
            ),
            (
                "streak_warning",
                "email/streak_warning.html",
                {
                    "display_name": "Alex",
                    "app_url": "http://127.0.0.1:5000",
                    "streak_count": 8,
                },
                "Don't lose your 8-day streak, Alex!",
            ),
            (
                "upgrade_confirmation",
                "email/upgrade_confirmation.html",
                {
                    "display_name": "Alex",
                    "app_url": "http://127.0.0.1:5000",
                },
                "You're on Ratio Pro — welcome to the full experience",
            ),
        ]

        # Email templates extend base_email.html, not base.html, so they
        # don't use the context_processor that requires a request context.
        # We render them directly via the Jinja environment to avoid needing
        # a fake request.
        from jinja2 import Environment, FileSystemLoader
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "templates")
        env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)

        for name, template, ctx, subject in templates:
            tmpl = env.get_template(template)
            html = tmpl.render(**ctx)
            out_path = os.path.join(OUTPUT_DIR, f"{name}.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  [rendered]  {out_path}")

            if recipient:
                from app.email_service import _send
                sent = _send(subject=subject, recipients=[recipient], html=html, text=f"Preview: {subject}")
                status = "sent" if sent else "FAILED (check MAIL_ENABLED / MAIL_PASSWORD in .env)"
                print(f"  [email]     {name} -> {recipient}: {status}")

    print()
    if not recipient:
        print(f"Open any file in  {OUTPUT_DIR}  to preview in your browser.")
        print("To also send live emails, run:  python scripts/test_emails.py --send your@email.com")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render and optionally send Ratio email templates.")
    parser.add_argument("--send", metavar="EMAIL", help="Send test emails to this address (requires MAIL_ENABLED=true in .env)")
    args = parser.parse_args()

    app = create_app()
    print("\nRendering email templates...\n")
    render_all(app, recipient=args.send)
