# Breaking Tests — LSATtutor Resilience Audit

Evidence of deliberate failure testing on 2026-06-10. Each scenario was exercised via `pytest tests/test_breaking.py` (automated) or a one-off probe script (manual confirmation).

## How to re-run

```bash
python -m pytest tests/test_breaking.py -v
python -m pytest tests/ -v
```

Manual wrong API key check: set `ANTHROPIC_API_KEY=sk-invalid` in `.env`, start the app with `python run.py`, log in, send a chat message. The tutoring service returns a friendly error in the chat UI (no stack trace).

---

## API failure tests

| Test | Before fix | After fix | Files changed |
|------|------------|-----------|---------------|
| Invalid `ANTHROPIC_API_KEY` | Graceful message in chat, but error text saved as assistant turn and daily quota consumed | Returns HTTP 503 with friendly JSON error; quota and history unchanged | `app/chat/claude_client.py`, `app/chat/routes.py`, `app/static/js/chat.js` |
| Wi-Fi disconnect (simulated `APIConnectionError`) | Graceful message, but quota consumed and error saved to history | HTTP 503 with connection message; quota not incremented | `app/chat/claude_client.py`, `app/chat/routes.py` |
| 10,000+ character input | Graceful — rejected at 3,000 chars with `400` | No change needed (already handled) | — |

---

## Input tests

| Test | Before fix | After fix | Files changed |
|------|------------|-----------|---------------|
| Empty input (Enter with nothing typed) | Client silently ignores; server returns `400` "Message is required." | No change needed | — |
| Special characters only (`!@#$%^&*()`) | Accepted and processed normally | No change needed | — |
| File path that doesn't exist | **N/A** — app has no user-supplied file path input | Substitute tested: upload `.png` with invalid magic bytes → flash error | — |
| URL `not-a-url` | **N/A** — app has no URL input fields | — | — |
| Invalid ICS duration (`not-a-number`) | **500** `ValueError` from bare `int()` | Flash: "Session duration must be a whole number of minutes." | `app/study_plan/routes.py` |

---

## Data tests

| Test | Before fix | After fix | Files changed |
|------|------------|-----------|---------------|
| Delete session file while logged in, then chat | Graceful — blank session recreated | No change needed | — |
| Delete user file while logged in, then visit profile | **Crash** — `AttributeError: 'NoneType' object has no attribute 'get'` | Force logout with flash: "Your saved data could not be read. Please sign in again." | `app/auth/helpers.py`, `app/profile/routes.py` |
| Corrupt `.enc` file (random bytes) | **500** `InvalidToken` uncaught | Force logout (HTML) or `401` JSON (API routes) | `app/storage/errors.py`, `app/storage/user_store.py`, `app/storage/session_store.py`, `app/auth/helpers.py`, route handlers |
| Missing data directory | Graceful at startup via `_ensure_data_dirs()`; `save_user` also creates nested dirs | No change needed | — |

---

## Additional fixes (global)

| Issue | Before fix | After fix | Files changed |
|-------|------------|-----------|---------------|
| Unhandled 500 errors | Werkzeug traceback in dev; generic 500 in prod | Custom handler returns friendly flash or JSON, logs server-side | `app/__init__.py` |
| Flask-Limiter 429 | Generic limiter page; chat JS showed "Something went wrong" | Custom 429 handler; chat JS parses server `error` field | `app/__init__.py`, `app/static/js/chat.js` |
| 413 oversized upload redirect | Used `request.referrer` (open-redirect risk) | Redirects to `url_for("profile.profile")` | `app/__init__.py` |
| Empty/unexpected Claude API response shape | Potential `IndexError` outside Anthropic handlers | Caught and returns fallback with `api_ok=False` | `app/chat/claude_client.py` |
| Corrupt data in template context processor | Could 500 every page render | Catches `StorageCorruptError`, returns safe default | `app/__init__.py` |

---

## Regression test coverage

`tests/test_breaking.py` — 12 tests covering the scenarios above.

Shared fixture extracted to `tests/conftest.py` for isolated temp data directories.

---

## Summary

- **Already resilient:** empty input, oversized input, special characters, missing session file, missing startup directories, avatar validation.
- **Bugs found and fixed:** orphaned sessions, corrupt encrypted files, quota burn on API failure, API errors saved as tutoring history, ICS duration crash, missing global error handlers, chat client not surfacing server errors.
- **Not applicable:** user-supplied file paths, URL inputs.
