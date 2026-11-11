"""IAP M8 tests: the log is structured, consistently fielded, and traceable by request_id.

The tests attach their own handler (using the app's real JsonFormatter) and parse
every line it writes, so they check the exact text an operator would read.
"""

import io
import json
import logging
import re
from contextlib import contextmanager
from unittest import mock

from django.db import OperationalError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from . import views
from .forms import ContactForm
from .models import Contact
from .observability import REQUEST_ID_HEADER, JsonFormatter

LEADING_FIELDS = ["ts", "level", "logger", "event", "request_id"]
TS_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


@contextmanager
def captured_log():
    """Capture everything the app and Django log, formatted exactly as in production."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.setLevel(logging.INFO)
    loggers = [logging.getLogger("tracker"), logging.getLogger("django")]
    for logger in loggers:
        logger.addHandler(handler)
    captured = {"raw": stream}
    try:
        yield captured
    finally:
        for logger in loggers:
            logger.removeHandler(handler)
        captured["text"] = stream.getvalue()
        captured["lines"] = [json.loads(line) for line in captured["text"].splitlines()]


def events_for(lines, request_id):
    return [line["event"] for line in lines if line["request_id"] == request_id]


VALID_CONTACT = {"name": "Secret Person", "email": "secret@example.com", "company": "Hidden Co", "stage": "meeting_scheduled"}


class StructuredLogFormatTests(TestCase):
    def test_every_line_is_json_with_the_same_leading_fields(self):
        with captured_log() as log:
            self.client.get(reverse("contact_list"))
            self.client.post(reverse("contact_list"), VALID_CONTACT)
            self.client.post(reverse("contact_list"), {"name": "", "stage": "new_lead"})
            self.client.get("/no-such-page/")
        self.assertGreaterEqual(len(log["lines"]), 10)
        for line in log["lines"]:
            self.assertEqual(list(line)[:5], LEADING_FIELDS, line)
            self.assertRegex(line["ts"], TS_FORMAT)
            self.assertIn(line["level"], {"INFO", "WARNING", "ERROR"})
            self.assertIsNotNone(line["request_id"], line)

    def test_line_written_outside_a_request_has_null_request_id(self):
        record = logging.LogRecord("tracker.test", logging.INFO, __file__, 1, "startup", None, None)
        line = json.loads(JsonFormatter().format(record))
        self.assertEqual(list(line)[:5], LEADING_FIELDS)
        self.assertIsNone(line["request_id"])
        self.assertEqual(line["event"], "tracker.test")  # not an app event, so named after its logger
        self.assertEqual(line["msg"], "startup")


class RequestTracingTests(TestCase):
    def test_one_add_contact_is_traceable_from_start_to_end(self):
        with captured_log() as log:
            response = self.client.post(reverse("contact_list"), VALID_CONTACT)
        request_id = response[REQUEST_ID_HEADER]
        self.assertEqual(events_for(log["lines"], request_id), ["request.start", "contact.created", "request.end"])
        created = next(line for line in log["lines"] if line["event"] == "contact.created")
        self.assertEqual(created["contact_id"], Contact.objects.get().pk)
        self.assertEqual(created["stage"], "meeting_scheduled")
        end = log["lines"][-1]
        self.assertEqual((end["event"], end["status"], end["method"]), ("request.end", 302, "POST"))

    def test_each_request_gets_its_own_id(self):
        first = self.client.get(reverse("contact_list"))[REQUEST_ID_HEADER]
        second = self.client.get(reverse("contact_list"))[REQUEST_ID_HEADER]
        self.assertRegex(first, r"^[0-9a-f]{16}$")
        self.assertNotEqual(first, second)

    def test_valid_incoming_request_id_is_reused(self):
        with captured_log() as log:
            response = self.client.get(reverse("contact_list"), headers={REQUEST_ID_HEADER: "upstream-abc-123"})
        self.assertEqual(response[REQUEST_ID_HEADER], "upstream-abc-123")
        self.assertEqual(
            events_for(log["lines"], "upstream-abc-123"), ["request.start", "contact.list.loaded", "request.end"]
        )

    def test_malformed_incoming_request_id_is_replaced(self):
        response = self.client.get(reverse("contact_list"), headers={REQUEST_ID_HEADER: "bad id; drop table"})
        self.assertRegex(response[REQUEST_ID_HEADER], r"^[0-9a-f]{16}$")

    def test_django_lines_written_after_the_middleware_keep_the_request_id(self):
        with captured_log() as log:
            response = self.client.get("/no-such-page/")
        request_id = response[REQUEST_ID_HEADER]
        self.assertEqual(events_for(log["lines"], request_id), ["request.start", "request.end", "django.request"])
        self.assertEqual(log["lines"][1]["level"], "WARNING")


class ContactEventPrivacyTests(TestCase):
    def test_rejected_contact_logs_field_names_not_values(self):
        with captured_log() as log:
            self.client.post(reverse("contact_list"), {"name": "", "email": "leak-check@not-valid", "stage": "new_lead"})
        rejected = next(line for line in log["lines"] if line["event"] == "contact.create.rejected")
        self.assertEqual(rejected["invalid_fields"], ["email", "name"])
        self.assertNotIn("leak-check", log["text"])

    def test_saved_contact_details_are_not_logged(self):
        with captured_log() as log:
            self.client.post(reverse("contact_list"), VALID_CONTACT)
        for value in ("Secret Person", "secret@example.com", "Hidden Co"):
            self.assertNotIn(value, log["text"])


class DatabaseFailureTests(TestCase):
    """The failure in docs/runbooks/RB-001: the list loads, but saving a contact gives a 500."""

    def test_failed_save_is_logged_with_cause_and_traceable_to_the_users_reference_code(self):
        self.client.raise_request_exception = False
        failure = OperationalError("attempt to write a readonly database")
        with mock.patch.object(ContactForm, "save", side_effect=failure), captured_log() as log:
            response = self.client.post(reverse("contact_list"), VALID_CONTACT)

        self.assertEqual(response.status_code, 500)
        request_id = response[REQUEST_ID_HEADER]
        # The user's error page shows the same ID the operator searches the log for.
        self.assertContains(response, f"Reference code: <code>{request_id}</code>", status_code=500)
        self.assertContains(response, "it was not saved", status_code=500)
        self.assertEqual(Contact.objects.count(), 0)

        self.assertEqual(
            events_for(log["lines"], request_id),
            ["request.start", "contact.create.failed", "django.request", "request.end"],
        )
        failed = next(line for line in log["lines"] if line["event"] == "contact.create.failed")
        self.assertEqual(failed["level"], "ERROR")
        self.assertEqual(failed["error_type"], "OperationalError")
        self.assertEqual(failed["error"], "attempt to write a readonly database")
        self.assertIn("db_ms", failed)
        crash = next(line for line in log["lines"] if line["event"] == "django.request")
        self.assertIn("Traceback", crash["stack"])
        self.assertEqual(log["lines"][-1]["status"], 500)

    def test_error_page_without_a_request_id_still_renders(self):
        response = views.server_error(RequestFactory().get("/"))
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Reference code: <code>unavailable</code>", response.content)
