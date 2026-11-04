# IAP M8 - Structured Logging and Runbook Entry

| Evidence asked for | Where it is |
|---|---|
| Sample structured log lines (field structure + a traced operation) | [`sample_logs.jsonl`](sample_logs.jsonl) (raw, exactly as written) and [`sample_logs_readable.txt`](sample_logs_readable.txt) (same lines via `scripts/logq.py`). Walkthrough below. |
| Runbook entry committed to the repository | [`docs/runbooks/RB-001-add-contact-error-page.md`](../runbooks/RB-001-add-contact-error-page.md) |
| Prompt-and-diff log | [`PROMPT_LOG_ENTRY.md`](PROMPT_LOG_ENTRY.md) (also appended to `/PROMPT_LOG.md`) and [`m8.diff`](m8.diff) |
| Tests | [`test_output.txt`](test_output.txt): 34 tests OK (23 existing, unchanged, plus 11 new), 100% statement and branch coverage |

## 1. What the log looks like

Every line is one JSON object ([JSON Lines](https://jsonlines.org/)). It is written to the terminal and to `logs/venture-crm.jsonl` (rotates at 5 MB, keeps 5 files; the folder is git-ignored). Every line starts with the same five fields, in the same order:

| Field | Meaning | Example |
|---|---|---|
| `ts` | UTC time, ISO 8601, milliseconds | `2026-11-04T20:39:00.728Z` |
| `level` | `INFO` / `WARNING` / `ERROR` | `INFO` |
| `logger` | which part of the code wrote it | `tracker.contacts` |
| `event` | stable, dot-separated name. Searched for, never reworded. | `contact.created` |
| `request_id` | correlation ID of the HTTP request (`null` outside a request) | `0e3f38397a17498b` |

These are followed by fields that belong to the event. They always have the same name and type:

| Event | Extra fields | When |
|---|---|---|
| `request.start` | `method`, `path` | every request, first line |
| `request.end` | `method`, `path`, `status`, `duration_ms` | every request, last line (`WARNING` for 4xx, `ERROR` for 5xx) |
| `contact.list.loaded` | `contact_count`, `db_ms` | the list page read the database |
| `contact.created` | `contact_id`, `stage`, `db_ms` | a contact was saved |
| `contact.create.rejected` | `invalid_fields` | the form failed validation |
| `contact.create.failed` | `error_type`, `error`, `db_ms` | the database refused the save |
| `django.request`, `django.security.*` | `msg` (+ `error_type`, `error`, `stack` on a crash) | lines Django itself writes, wrapped in the same format |

**No contact data is logged.** Names, emails and companies never appear. Events carry IDs, field names and counts only, because this app will hold real contacts after the course. A test enforces this (`ContactEventPrivacyTests`), and the sample file contains none of the values that were submitted.

## 2. A single operation, traced

**Choice of correlating identifier:** this app is a single process with no queue or downstream service, so one user action is one HTTP request. A per-request `request_id` is therefore the right ID. `RequestLoggingMiddleware` creates it as the first thing that runs, keeps it in a `contextvars.ContextVar` (so every line written while handling that request carries it, including Django's own), returns it in the `X-Request-ID` header, and shows it to the user as the **Reference code** on the error page. An incoming `X-Request-ID` is reused if it looks like an ID, so a proxy placed in front later could pass its own ID through.

A user adds "Ada Demo". Filter the log on her request's ID, `0e3f38397a17498b`:

```json
{"ts": "2026-11-04T20:39:00.711Z", "level": "INFO", "logger": "tracker.request", "event": "request.start", "request_id": "0e3f38397a17498b", "method": "POST", "path": "/"}
{"ts": "2026-11-04T20:39:00.728Z", "level": "INFO", "logger": "tracker.contacts", "event": "contact.created", "request_id": "0e3f38397a17498b", "contact_id": 1, "stage": "meeting", "db_ms": 2.7}
{"ts": "2026-11-04T20:39:00.732Z", "level": "INFO", "logger": "tracker.request", "event": "request.end", "request_id": "0e3f38397a17498b", "method": "POST", "path": "/", "status": 302, "duration_ms": 21.1}
```

The same save failing (database made read-only on purpose). The user's error page said **Reference code: 79338936766b4443**, and filtering on that code gives the whole story, cause included:

```json
{"ts": "2026-11-04T20:39:00.770Z", "level": "INFO", "logger": "tracker.request", "event": "request.start", "request_id": "79338936766b4443", "method": "POST", "path": "/"}
{"ts": "2026-11-04T20:39:00.772Z", "level": "ERROR", "logger": "tracker.contacts", "event": "contact.create.failed", "request_id": "79338936766b4443", "error_type": "OperationalError", "error": "attempt to write a readonly database", "db_ms": 0.8}
{"ts": "2026-11-04T20:39:00.772Z", "level": "ERROR", "logger": "django.request", "event": "django.request", "request_id": "79338936766b4443", "msg": "Internal Server Error: /", "error_type": "OperationalError", "error": "attempt to write a readonly database", "stack": "Traceback (most recent call last): ... (full trace in sample_logs.jsonl)"}
{"ts": "2026-11-04T20:39:00.781Z", "level": "ERROR", "logger": "tracker.request", "event": "request.end", "request_id": "79338936766b4443", "method": "POST", "path": "/", "status": 500, "duration_ms": 11.2}
```

`python scripts/logq.py 79338936766b4443` prints the same thing in readable form, without grep or jq, so it works on Windows too.

## 3. The runbook entry

[RB-001](../runbooks/RB-001-add-contact-error-page.md) starts from what an operator is first told ("I clicked Add contact and got an error page"), not from a cause. It then works through these steps:

1. **Find the request**: `logq.py --failed`, or the user's reference code.
2. **Confirm the diagnosis**: the `error` field, plus one check anyone can do (does the list page still load?), separates the three plausible causes.
3. **Fix each cause**, with macOS/Linux and Windows commands: read-only file or folder, a lock held by another program (for example DB Browser for SQLite with unsaved edits), or a missing/empty database file.
4. **Verify** the fix with a test contact, confirm `contact.created` in the log, delete the test contact.
5. **Escalate**, saying exactly what evidence to send.

It puts the two dangerous moves first: deleting `db.sqlite3`, which is not in Git, and running `migrate` against an empty file, which makes it look as if every contact is gone.

**How it was tested:** all three failures were reproduced on a running server (as a non-root user, so file permissions are really enforced). Every command in the runbook was run against them, and the log excerpts in the runbook are real output.

## 4. Code changes

| File | Change |
|---|---|
| `tracker/observability.py` (new) | `JsonFormatter`, `log_event()`, `RequestLoggingMiddleware` (request_id + `request.start`/`request.end`) |
| `tracker/views.py` | `contact.*` events in `add_contact` / `show_contact_page`. A `DatabaseError` on save is logged as `contact.create.failed` and then re-raised, so the response is still a 500. New `server_error` view (custom 500 page that shows the reference code). |
| `ventureCRM/settings.py` | middleware registered first. `LOGGING` routes app and Django logs through the JSON formatter. runserver's duplicate free-text access line is dropped. `DEBUG` can be turned off with `DJANGO_DEBUG=False` (default unchanged: on). `ALLOWED_HOSTS` set to localhost. |
| `ventureCRM/urls.py` | `handler500` |
| `scripts/logq.py` (new) | stdlib log reader used by the runbook |
| `tracker/test_logging.py` (new) | 11 tests: format and field order, tracing, ID reuse/replacement, privacy, the RB-001 failure end-to-end |

**Behaviour visible to users is unchanged**, except that each response now carries an `X-Request-ID` header, and the error page shows a reference code when DEBUG is off. All 23 existing tests pass unchanged.
