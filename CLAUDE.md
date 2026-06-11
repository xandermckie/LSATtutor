# CLAUDE.md

## Project Overview
Ratio is a Flask-based LSAT tutoring web app. It helps users break down LSAT questions, notice patterns, track weak areas, and stay on a study schedule. Target users are undergraduates and others preparing for the LSAT in the coming months. The app differentiates from a plain chatbot by combining structured question practice, weak-area tracking, gamification (XP, leagues, streaks, daily missions, friend challenges), a personalized study plan, and a Pomodoro focus timer — all behind a single login.

## Architecture

### Blueprint structure
Each feature is its own Flask blueprint registered in `app/__init__.py`:
- `auth` — register, login, logout, terms
- `chat` — AI tutor chat (Haiku model), clear history
- `analysis` — weak area dashboard
- `study_plan` — generate/fix plan (Sonnet model), export .ics, send reminder email
- `quiz` — practice questions from `app/static/questions.json`
- `profile` — avatar, username, password, export CSV, delete account, Pomodoro intro dismiss
- `social` — leaderboard, friends, challenges, XP engine, missions, daily streak
- `billing` — upgrade to Pro (mock payment), downgrade

### Data storage
- **Users**: one encrypted JSON file per user in `data/users/`, keyed by SHA256(email). Loaded via `app/storage.py` with a 30-second in-process LRU cache (`load_user_cached`).
- **Sessions (chat history)**: separate encrypted JSON per user in `data/sessions/`.
- **Avatars**: binary files in `data/avatars/`, named by SHA256(email).
- All JSON at rest is encrypted with Fernet (`FERNET_KEY` in `.env`). Passwords are bcrypt-hashed and stored inside the encrypted blob.
- No SQLite — JSON was the deliberate choice for familiarity.

### AI models
- Chat (tutor): `claude-haiku-4-5-20251001` — fast, cheap, conversational.
- Study plan generation: `claude-sonnet-4-6` — higher quality for structured output.
- Both calls are rate-limited via Flask-Limiter and responses are cached with diskcache where possible.

### Extensions (`app/extensions.py`)
- `limiter` — Flask-Limiter (rate limiting on all API-touching routes)
- `mail` — Flask-Mail (Gmail SMTP with App Password)
- `csrf` — Flask-WTF CSRFProtect (global CSRF protection)
- `get_cache()` — diskcache.Cache factory (response caching)

### Security implemented
- Fernet encryption on all user data at rest
- bcrypt password hashing
- CSRF protection: `CSRFProtect` globally + `csrf_token()` hidden input on every POST form + `X-CSRFToken` header on every `fetch()` call
- `Cache-Control: no-store` on every response (prevents stale session pages)
- `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`
- `@login_required` decorator on every authenticated route
- Rate limits on all routes that touch the API or mutate user data
- Error handlers redirect to `url_for("index")` — never `request.referrer` (prevents open redirect)
- Avatar uploads: extension whitelist + magic byte check + 2 MB cap
- Username input: regex whitelist `[^\w\s\-]` stripped, max 50 chars

## Key Decisions Made During Build

- **Glassmorphism UI**: `backdrop-filter: blur(18px)` cards on a radial-gradient body. `.glass-card` uses `overflow: visible` (not `hidden`) so absolutely-positioned badges aren't clipped.
- **Free vs Pro tiers**: Free gets 25 chat/day, 50 quiz/day, 1 study plan + 1 date correction. Pro gets unlimited chat, quiz, and study plan edits. Friends, challenges, and leaderboard are open to everyone.
- **Mock payment**: No real payment processor. Any 16-digit number, MM/YY, CVV passes. Sets `user["tier"] = "pro"` in the JSON.
- **Email**: Flask-Mail + Gmail App Password. `MAIL_PASSWORD` has spaces stripped in `config.py` because Gmail displays App Passwords with spaces but SMTP rejects them. `MAIL_ENABLED=true` in `.env` gates all email sends.
- **Question bank**: 100 hand-written LSAT questions in `app/static/questions.json`, loaded lazily at first request and module-cached. Covers all major types: Weaken, Strengthen, Assumption, Flaw, Inference, Main Point, Parallel Reasoning, Principle, Resolve, Reading Comprehension.
- **Gamification**: XP awarded for correct quiz answers and chat turns. Leagues: Bronze/Silver/Gold/Platinum/Diamond based on XP thresholds. Daily missions (3/day, refreshed at midnight). 24-hour friend challenges (XP Race, Question Blitz, Accuracy Duel). Leaderboard shows top 50 by XP.
- **Pomodoro timer**: Vanilla JS widget injected into every page via `base.html`. State persists in `localStorage` across navigation. Shows intro popup once per account, dismissed via POST.
- **Study plan calendar export**: Generates `.ics` file for Apple/Outlook; Google Calendar link built client-side via URL params.
- **Context processor**: `inject_ui_prefs()` in `app/__init__.py` injects `logged_in`, `streak_count`, `xp_info`, `missions`, `current_tier`, `display_name` into every template. Uses `load_user_cached` — safe to call on every request.
- **Nav auth guard**: Nav uses `{% if logged_in %}` from the context processor (which validates the session) rather than `session.get('email')` alone — prevents showing authenticated links from a cached page.

## Constraints
- Never commit `.env` or any file containing API keys
- Error handling must be explicit — no bare `except` clauses; always `except Exception as exc: logger.warning(...)`
- Every function must have a docstring
- User data must be encrypted at rest (Fernet) and passwords bcrypt-hashed
- Rate limiting must be in place for all routes that call the API or mutate data
- Cacheable responses should use diskcache
- Every POST form must include `{{ csrf_token() }}` as a hidden input
- Error handler redirects must use `url_for(...)` — never `request.referrer`
- `@login_required` must be applied to every authenticated route (no manual session checks)
- Username and any user-supplied display strings must be sanitized with a character whitelist before storing

## Environment Variables (`.env`)
```
SECRET_KEY=...
ANTHROPIC_API_KEY=...
FERNET_KEY=...          # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MAIL_ENABLED=true
MAIL_USERNAME=you@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx   # Gmail App Password — spaces are stripped automatically
APP_URL=http://127.0.0.1:5000
```

## Running the app
```
pip install -r requirements.txt
flask run
```

## Resolved Open Questions

- **Calendar integration**: Done — `.ics` export + Google Calendar deep-link built client-side.
- **Response caching**: diskcache is wired in `app/extensions.py`; study plan responses are cached by prompt hash.
- **Differentiation from plain chatbot**: Structured weak-area tracking, question bank with typed LSAT questions, gamification (XP/leagues/streaks/missions/challenges), personalized study plan with calendar export, Pomodoro timer.
- **Context management**: Chat history stored per-session in encrypted JSON; full history is passed to the AI on each turn (no compression yet — open item if history grows very long).
- **Tutoring environment**: AI tutor chat page with Lex the owl mascot. Quiz is separate from chat — question bank with A/D choices, immediate feedback and explanation.

## Still Open
- Chat context compression for very long histories (currently full history sent each turn)
- Real payment processor integration (Stripe) if app goes live
- Push notifications / native mobile support
- Admin dashboard for monitoring usage
