"""
M6 acceptance tests for the M5 thin slice: "add a contact".

These tests drive the app the same way a browser does. Django's
LiveServerTestCase starts a real HTTP server on a free port, and the test
talks to it over a real socket with urllib. Nothing is mocked or stubbed:

    HTTP GET  -> URL router -> view -> template (form + CSRF token)
    HTTP POST -> CSRF middleware -> URL router -> view -> ContactForm
              -> Django ORM -> SQLite -> 302 redirect
    HTTP GET  -> view -> ORM reads the database -> rendered contact table

Unlike the test client used in tracker/tests.py, the live server enforces
CSRF protection, so the tests must fetch the page first and send the token
back, exactly as a user's browser would.
"""

import http.cookiejar
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from django.test import LiveServerTestCase

from .models import Contact
from .testing import TEST_PASSWORD, TEST_USERNAME, make_test_user


class _ContactTableParser(HTMLParser):
    """Pulls the visible text of each row in the contacts <tbody>."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self._in_tbody = False
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tbody":
            self._in_tbody = True
        elif self._in_tbody and tag == "tr":
            self._row = []
        elif self._row is not None and tag == "td":
            self._cell = ""

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._in_tbody = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
        elif tag == "td" and self._cell is not None:
            self._row.append(self._cell.strip())
            self._cell = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell += data


class Browser:
    """A minimal cookie-keeping HTTP user agent (stand-in for a real browser)."""

    def __init__(self, base_url):
        self.base_url = base_url
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def get(self, path="/"):
        with self.opener.open(self.base_url + path) as resp:
            return resp.status, resp.geturl(), resp.read().decode("utf-8")

    def sign_in(self, username, password):
        """Fill in the real login form (US-8), CSRF token included, and follow the redirect."""
        _, _, page = self.get("/login/")
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page).group(1)
        body = urllib.parse.urlencode(
            {"username": username, "password": password, "csrfmiddlewaretoken": token}
        ).encode()
        request = urllib.request.Request(self.base_url + "/login/", data=body, method="POST")
        with self.opener.open(request) as resp:
            return resp.status, resp.geturl(), resp.read().decode("utf-8")

    def submit_contact_form(self, fields, include_csrf=True):
        """Load the page, then submit the add-contact form like a user clicking 'Add contact'."""
        _, _, page = self.get("/")
        data = dict(fields)
        if include_csrf:
            token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page).group(1)
            data["csrfmiddlewaretoken"] = token
        body = urllib.parse.urlencode(data).encode()
        request = urllib.request.Request(self.base_url + "/", data=body, method="POST")
        # urllib follows the 302 Post/Redirect/Get automatically, like a browser.
        with self.opener.open(request) as resp:
            return resp.status, resp.geturl(), resp.read().decode("utf-8")


def table_rows(html):
    parser = _ContactTableParser()
    parser.feed(html)
    return parser.rows


class AddContactAcceptanceTests(LiveServerTestCase):
    """User story: as a founder, I can add a contact and immediately see it in my list."""

    def setUp(self):
        make_test_user()
        self.browser = Browser(self.live_server_url)
        self.browser.sign_in(TEST_USERNAME, TEST_PASSWORD)

    def test_user_adds_contact_and_sees_it_in_the_list(self):
        status, final_url, page = self.browser.submit_contact_form(
            {"name": "Jane Demo", "email": "jane@example.com", "company": "Demo Labs", "stage": "contacted"}
        )

        # Post/Redirect/Get: the user lands back on the list page, not a re-POSTable form.
        self.assertEqual(status, 200)
        self.assertEqual(final_url.rstrip("/"), self.live_server_url)

        # What the user sees: one row with every field they entered, stage shown by its label.
        self.assertIn("1 saved in database", page)
        rows = table_rows(page)
        self.assertEqual(len(rows), 1)
        name, company, email, stage, added = rows[0]
        self.assertEqual((name, company, email, stage), ("Jane Demo", "Demo Labs", "jane@example.com", "Contacted"))
        self.assertNotEqual(added, "")

        # And it really was persisted (survives a fresh page load).
        _, _, reloaded = self.browser.get("/")
        self.assertEqual(table_rows(reloaded)[0][0], "Jane Demo")
        self.assertEqual(Contact.objects.get().email, "jane@example.com")

    def test_newest_contact_appears_at_the_top_of_the_list(self):
        self.browser.submit_contact_form({"name": "First Founder", "stage": "new_lead"})
        _, _, page = self.browser.submit_contact_form({"name": "Second Founder", "stage": "meeting_scheduled"})

        names = [row[0] for row in table_rows(page)]
        self.assertEqual(names, ["Second Founder", "First Founder"])
        self.assertIn("2 saved in database", page)

    def test_invalid_submission_shows_errors_and_saves_nothing(self):
        status, _, page = self.browser.submit_contact_form({"name": "", "email": "not-an-email", "stage": "new_lead"})

        self.assertEqual(status, 200)
        self.assertIn("errorlist", page)                # user is told what is wrong
        self.assertIn('value="not-an-email"', page)    # their input is kept so they can fix it
        self.assertIn("0 saved in database", page)
        self.assertEqual(Contact.objects.count(), 0)

    def test_post_without_csrf_token_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.browser.submit_contact_form({"name": "Forged Contact", "stage": "new_lead"}, include_csrf=False)

        self.assertEqual(ctx.exception.code, 403)
        self.assertEqual(Contact.objects.count(), 0)


class SignInAcceptanceTests(LiveServerTestCase):
    """User story US-8: my contacts are only visible after I sign in."""

    def test_signed_out_visitor_is_sent_to_the_login_page(self):
        status, final_url, page = Browser(self.live_server_url).get("/")
        self.assertEqual(status, 200)
        self.assertEqual(final_url, self.live_server_url + "/login/?next=/")
        self.assertIn("Sign in", page)
        self.assertNotIn("Contacts (", page)

    def test_correct_password_signs_in_and_shows_the_contacts(self):
        make_test_user()
        status, final_url, page = Browser(self.live_server_url).sign_in(TEST_USERNAME, TEST_PASSWORD)
        self.assertEqual((status, final_url), (200, self.live_server_url + "/"))
        self.assertIn("saved in database", page)

    def test_wrong_password_stays_on_the_login_page_with_an_error(self):
        make_test_user()
        status, final_url, page = Browser(self.live_server_url).sign_in(TEST_USERNAME, "wrong-password")
        self.assertEqual(final_url, self.live_server_url + "/login/")
        self.assertIn("errorlist", page)
