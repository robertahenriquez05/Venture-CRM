# IAP M6 - Tests and Bug-Injection Demonstration

Thin slice under test (from M5): **"Add a contact"**. The browser form goes through the URL router, the `contact_list` view, `ContactForm` validation, the Django ORM and SQLite, then the contact table is rendered back to the page.

## 1. Test suite

| File | Kind | What it covers |
|---|---|---|
| `tracker/test_acceptance.py` | Acceptance (4 tests) | Starts a **real HTTP server** (`LiveServerTestCase`) and drives it over a socket with `urllib`, the way a browser would: it GETs the page, reads the CSRF token, POSTs the form, follows the 302 redirect, and parses the rendered contact table. Nothing is mocked. The tests cover: adding a contact and seeing every field in the list, the newest contact appearing at the top, an invalid submission showing errors and saving nothing, and a forged POST without a CSRF token getting a 403. |
| `tracker/test_forms.py` | Unit (11 tests) | The `ContactForm` rules: name is required, a whitespace-only name is rejected, the name-length boundary (120 characters accepted, 121 rejected), email and company are optional, malformed emails are rejected, only the 5 pipeline stages are accepted, saving stores exactly what was entered, and surrounding whitespace is trimmed. |
| `tracker/test_models.py` | Unit (5 tests) | The `Contact` model: default stage is Lead, `created_at` is set automatically, the display name and stage labels, and **contacts come back newest first**. Timestamps are pinned, so the result doesn't depend on clock resolution. |
| `tracker/tests.py` | M5 walking-skeleton tests (3) | Unchanged from M5. |

The unit tests check behaviour a user would notice (what is accepted, rejected, saved, or shown, and in what order). They don't restate how the form or model is built.

**Run it:** `coverage run manage.py test --verbosity 2`, which gives **23 tests, all passing**. Full output: [`test_output.txt`](test_output.txt).

## 2. Coverage report

`coverage report` gives **100% statement and 100% branch coverage** of `tracker/` and `ventureCRM/`. Migrations, test files and the asgi/wsgi entry points are excluded in `.coveragerc`.
- Text report: [`coverage_report.txt`](coverage_report.txt)
- HTML report: [`coverage_html/index.html`](coverage_html/index.html)
- CI now runs the suite under `coverage`, prints the report, and uploads the HTML report as a build artifact (`.github/workflows/main.yml`).

## 3. Bug-injection demonstration

### The fault
I changed **one character** in `tracker/models.py`: `ordering = ["-created_at"]` became `ordering = ["created_at"]`.

With this fault the app still loads, still saves contacts, and throws no errors. But the contact list silently flips to **oldest first**, so the founder I added a minute ago ends up at the bottom of a growing list instead of at the top. A user would care, because the most recent contacts are the ones that need follow-up. This is a single inverted sort direction, not a deleted function.

| Artifact | File |
|---|---|
| (a) Fault diff | [`bug_injection/01_fault.diff`](bug_injection/01_fault.diff) |
| (b) Suite failing on the fault | [`bug_injection/02_suite_failing.txt`](bug_injection/02_suite_failing.txt): 23 tests ran, **2 failed**. The unit test `test_contacts_come_back_newest_first` and the acceptance test `test_newest_contact_appears_at_the_top_of_the_list` both report the reversed order. |
| (c) Fix restoring green | [`bug_injection/03_fix_restored_green.txt`](bug_injection/03_fix_restored_green.txt): after the fault was reverted, 23 tests ran and all passed. |

### Finding: the M5 suite would not have caught this
Before writing the new tests, I ran the original M5 walking-skeleton suite against the same fault ([`bug_injection/00_m5_suite_misses_fault.txt`](bug_injection/00_m5_suite_misses_fault.txt)). **All 3 tests passed with the bug in place, at 99% line coverage and 100% branch coverage.** None of those tests ever added more than one contact, so the order of the list was never checked.

This is the gap the assignment warns about: a coverage number close to 100% said nothing about whether the list order was correct. The two ordering tests in M6 were written to close that gap. They catch the fault at both levels: in the database query (unit) and on the rendered page (acceptance).

## How to reproduce on your own machine
```
coverage run manage.py test --verbosity 2     # 23 tests, OK
coverage report                               # 100%
# In tracker/models.py, change  "-created_at"  to  "created_at"
python manage.py test                         # FAILED (failures=2)
git checkout -- tracker/models.py             # revert
python manage.py test                         # OK
```
