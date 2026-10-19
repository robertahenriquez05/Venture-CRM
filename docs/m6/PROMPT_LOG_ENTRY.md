
## IAP M6 - Tests and Bug-Injection Demonstration (2026-10-19)

**Tool:** Claude (Claude Code session, with read/write access to my local repo folder)

**Prompt:** Pasted the full IAP M6 assignment text and asked Claude to write an acceptance test for my M5 thin slice ("add a contact"), unit tests for the logic underneath it, a coverage report, and a bug-injection demonstration (fault diff, failing run, fix restoring green).

**What the AI produced (diff summary):**
- `tracker/test_acceptance.py` (new) - 4 acceptance tests run against a real live HTTP server (LiveServerTestCase + urllib, real CSRF token, real redirect, parses the rendered contact table)
- `tracker/test_forms.py` (new) - 11 unit tests for ContactForm validation and saving (required name, whitespace-only name, 120/121 char boundary, optional email/company, bad emails, valid/invalid stages, trimming)
- `tracker/test_models.py` (new) - 5 unit tests for Contact (default stage, created_at, labels, newest-first ordering with pinned timestamps)
- `.coveragerc` (new) - measure tracker/ and ventureCRM/ with branch coverage; omit migrations, tests, asgi/wsgi
- `requirements.txt` - added coverage==7.16.2
- `.github/workflows/main.yml` - CI now runs `coverage run manage.py test`, prints `coverage report`, uploads the HTML report as an artifact
- `docs/m6/` (new) - test_output.txt, coverage_report.txt, coverage_html/, bug_injection/ evidence files, README.md write-up
- No application code was changed. tracker/tests.py (M5) was left as is.

**What I changed / decided:**
- Chose the injected fault: flipping `ordering = ["-created_at"]` to `["created_at"]` in tracker/models.py. One character, no crash, but the contact list silently shows oldest-first, which a user would notice and care about.
- Ran the original M5 suite against the fault first: it still passed (3/3) at 99% line / 100% branch coverage. Recorded this as a genuine finding; the new ordering tests (unit + acceptance) are the tests that close that gap.
- Kept the acceptance test dependency-free (stdlib urllib instead of Selenium) so CI needs no browser.

**Verification:** 23/23 tests pass; coverage 100% statements and branches; with the fault injected 2 tests fail (one unit, one acceptance); after reverting, 23/23 pass again. `manage.py check` and `makemigrations --check` are clean.
