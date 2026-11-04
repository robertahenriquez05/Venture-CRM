"""Structured logging for Venture CRM (IAP M8).

Every log line the app writes is one JSON object on one line ("JSON Lines").
Every line has the same first five fields, in the same order:

    ts          UTC timestamp, ISO 8601 with milliseconds, e.g. 2026-11-04T20:31:07.412Z
    level       INFO / WARNING / ERROR
    logger      which part of the code wrote it, e.g. tracker.request
    event       a stable, dot-separated name, e.g. contact.created
    request_id  the correlation ID of the HTTP request the line belongs to
                (null for lines written outside a request, e.g. at startup)

After those come the fields that belong to that event (status, duration_ms,
contact_id, ...). Lines that Django itself writes (logger "django.*") get the
same five fields, with the original text in "msg".

Correlation: RequestLoggingMiddleware gives each request a request_id, keeps it
in a context variable for the life of the request (so any log line written
while handling that request carries it automatically), and returns it to the
caller in the X-Request-ID response header.

Privacy: contact names, emails and companies are never logged. Events carry
IDs, field names and counts only, because this app will hold real contact
data after the course.
"""

import contextvars
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone

REQUEST_ID_HEADER = "X-Request-ID"

# An incoming X-Request-ID is reused only if it looks like an ID, so a caller
# cannot inject newlines or huge values into the log.
_VALID_INCOMING_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

_request_id = contextvars.ContextVar("request_id", default=None)

log = logging.getLogger("tracker.request")


def current_request_id():
    """The request_id of the request being handled on this thread, or None."""
    return _request_id.get()


def log_event(logger, level, event, **fields):
    """Write one structured event. `event` is the stable name; `fields` are its data."""
    logger.log(level, event, extra={"event_fields": fields})


class JsonFormatter(logging.Formatter):
    """Formats every log record as a single-line JSON object with a fixed field order."""

    def format(self, record):
        fields = getattr(record, "event_fields", None)
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            # App events name themselves; a line from Django is named after its logger.
            "event": record.getMessage() if fields is not None else record.name,
            "request_id": _request_id.get() or _request_id_from_record(record),
        }
        if fields is not None:
            entry.update(fields)
        else:
            entry["msg"] = record.getMessage()
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            entry["error_type"] = exc_type.__name__
            entry["error"] = str(exc_value)
            entry["stack"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


def _request_id_from_record(record):
    """Django logs some lines (e.g. "Not Found") after our middleware has finished.

    Those records carry the request object, which still has the request_id we gave it.
    """
    return getattr(getattr(record, "request", None), "request_id", None)


def _level_for_status(status):
    if status >= 500:
        return logging.ERROR
    if status >= 400:
        return logging.WARNING
    return logging.INFO


class RequestLoggingMiddleware:
    """Assigns the request_id and writes request.start / request.end for every request.

    Listed first in MIDDLEWARE so it wraps everything else, including Django's
    500 handling: a crashed request still gets a request.end line with status 500.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _VALID_INCOMING_ID.match(incoming) else uuid.uuid4().hex[:16]
        token = _request_id.set(request_id)
        request.request_id = request_id
        started = time.perf_counter()
        try:
            log_event(log, logging.INFO, "request.start", method=request.method, path=request.path)
            response = self.get_response(request)
            response[REQUEST_ID_HEADER] = request_id
            log_event(
                log,
                _level_for_status(response.status_code),
                "request.end",
                method=request.method,
                path=request.path,
                status=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            return response
        finally:
            _request_id.reset(token)
