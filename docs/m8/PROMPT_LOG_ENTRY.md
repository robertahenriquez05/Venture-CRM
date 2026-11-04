## IAP M8 - Structured Logging and Runbook Entry (2026-11-04)

**Tool:** Claude (claude.ai session with a cloud workspace and push access to this repo)

**Prompt:** Pasted the full IAP M8 assignment text ("Add structured logging to your app... Include whatever correlating identifier makes sense... Write one runbook entry for a failure your app could plausibly have... for someone who is not you, at an hour when you are not available") plus the rubric, and asked Claude to help me do it for my individual Venture CRM project and get it submitted.

**What the AI did:**
- Read the app and the M5-M7 history, ran the existing suite first (23 tests OK, 100% coverage).
- Added `tracker/observability.py`: a JSON formatter with a fixed leading field order (`ts, level, logger, event, request_id`), a `log_event()` helper, and `RequestLoggingMiddleware`, which creates a per-request `request_id`, stores it in a context variable, logs `request.start`/`request.end`, and returns it in `X-Request-ID`.
- Added `contact.list.loaded`, `contact.created`, `contact.create.rejected`, `contact.create.failed` events to `tracker/views.py`, plus a custom 500 page that shows the request_id as a reference code.
- Configured `LOGGING` in settings: Django's own loggers go through the same JSON formatter, logs go to the terminal and `logs/venture-crm.jsonl`, and runserver's duplicate access line is dropped.
- Reproduced three real failures on a running server (read-only database, database locked by another program, missing tables), wrote the runbook from what the logs actually showed, and ran every runbook command against those failures.
- Wrote `scripts/logq.py` so the runbook works without grep/jq (Windows too), and 11 new tests in `tracker/test_logging.py`.

**Diff:** `docs/m8/m8.diff`. App code: `tracker/views.py`, `ventureCRM/settings.py`, `ventureCRM/urls.py`, `.gitignore`, and new `tracker/observability.py`. No existing test file changed.

**What I changed / decided:**
- **Correlating ID = per-request ID**, not a per-contact or session ID: in this app one user action is one HTTP request (no queue, no background jobs), so the request is the unit of work to trace.
- **No contact data in logs** (names, emails, companies). Only IDs, field names and counts, because I plan to use this app with real contacts after the course. A test enforces this.
- **Picked "Add contact shows an error page"** as the runbook failure, because it is the one thing a user would actually report. I made sure it starts from that symptom and branches to causes, rather than starting from "SQLite is locked".
- Kept `DEBUG` on by default so my day-to-day workflow does not change; `DJANGO_DEBUG=False` shows the real user-facing error page.
- Excluded the log-file branch in settings from coverage (`pragma: no cover`), because tests never write the log file on purpose; it was verified by hand (`sample_logs.jsonl` was written by it).

**Verification:** 34/34 tests pass (23 unchanged + 11 new) at 100% statement and branch coverage; `manage.py check` and `makemigrations --check` are clean. `docs/m8/sample_logs.jsonl` was produced by a real `runserver` process; grep confirms no submitted contact values appear in it.
