"""
M7 characterization check (run before AND after the refactor).

The test suite is the main proof the refactor preserved behaviour. This script
is a second, wider net: it sends every kind of request the "/" URL can receive
- including PUT and DELETE, which no test exercises - and prints a fingerprint
of each response (status, redirect target, rows saved, and a SHA-256 of the
page with the per-request CSRF token and timestamps blanked out).

If the "before" and "after" outputs are identical, the view answers every
request exactly the same way it did before.

Run from the repo root:   python docs/m7/characterize.py
It uses a throwaway in-memory test database; db.sqlite3 is never touched.
"""

import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ventureCRM.settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402

from tracker.models import Contact  # noqa: E402


def fingerprint(html):
    html = re.sub(r'name="csrfmiddlewaretoken" value="[^"]+"', 'name="csrfmiddlewaretoken" value="X"', html)
    html = re.sub(r"<td>[A-Z][a-z]{2}\.? \d{1,2}, \d{4} \d{1,2}:\d{2} [ap]\.m\.</td>", "<td>TIMESTAMP</td>", html)
    return hashlib.sha256(html.encode()).hexdigest()[:16]


def main():
    setup_test_environment()
    old_name = connection.creation.create_test_db(verbosity=0)
    try:
        client = Client()
        cases = [
            ("GET  / (empty list)", lambda: client.get("/")),
            ("HEAD /", lambda: client.head("/")),
            ("POST / valid contact", lambda: client.post("/", {"name": "Jane Demo", "email": "jane@example.com", "company": "Demo Labs", "stage": "contacted"})),
            ("GET  / (one contact)", lambda: client.get("/")),
            ("POST / invalid (blank name, bad email)", lambda: client.post("/", {"name": "", "email": "not-an-email", "stage": "lead"})),
            ("POST / invalid (unknown stage)", lambda: client.post("/", {"name": "Bob", "stage": "won"})),
            ("POST / second valid contact", lambda: client.post("/", {"name": "Second Founder", "stage": "meeting"})),
            ("GET  / (two contacts)", lambda: client.get("/")),
            ("PUT  /", lambda: client.put("/")),
            ("DELETE /", lambda: client.delete("/")),
        ]
        for label, send in cases:
            resp = send()
            body = resp.content.decode()
            print(
                f"{label:<40} status={resp.status_code}  "
                f"location={resp.get('Location', '-'):<3}  "
                f"contacts_in_db={Contact.objects.count()}  "
                f"body_sha256={fingerprint(body) if body else '(empty)'}"
            )
    finally:
        connection.creation.destroy_test_db(old_name, verbosity=0)


if __name__ == "__main__":
    main()
