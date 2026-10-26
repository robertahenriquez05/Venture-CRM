
## IAP M7 - Documented Refactor (2026-10-26)

**Tool:** Claude (Claude Code session, with read/write access to my local repo folder)

**Prompt:** Pasted the full IAP M7 assignment text ("Improve the internal structure of your app without changing what it does, and prove that is what happened... Run the same tests before and after. They must pass both times, unchanged.") and asked Claude to help with it for my individual Venture CRM project.

**What the AI did:**
- Read the whole app and picked the smell: `contact_list` in `tracker/views.py` mixed two jobs (list and create), and the invalid-POST path had no `return` of its own. It fell through into the GET list-building code (Divergent Change plus a fall-through conditional).
- Before touching any code, ran the full M6 suite (23 tests, OK, 100% coverage) and wrote `docs/m7/characterize.py`, a characterization script that fingerprints the response to GET, HEAD, valid/invalid POST, PUT and DELETE.
- Refactored `tracker/views.py` with Extract Function: `contact_list` (dispatch only), `add_contact` (validate and save, with a guard clause), `show_contact_page` (render), and `contacts_for_list` (the one place the list query lives). The template name is now a constant.
- Re-ran the same suite and the same script after the refactor.

**Diff:** `docs/m7/refactor.diff`. Only `tracker/views.py` changed in application code: 35 insertions, 10 deletions. No test file, URL, template, model or form was changed.

**What I changed / decided:**
- Kept the view name `contact_list` and the URL as they were, so `reverse("contact_list")` and `tracker/urls.py` didn't need to change. The tests had to stay untouched, so this was required anyway.
- The characterization check showed that PUT and DELETE to `/` return the list page (200) instead of 405. I chose to **keep** that behaviour in this refactor, because fixing it changes behaviour. I noted it as a separate future fix.
- Chose this smell over moving the template's inline CSS into a base template. The view problem affects correctness when the next features (search, filters, detail page) are added; the CSS one is only tidiness.

**Verification:** before the refactor, 23/23 passed at 100% statements and branches. After, the same 23/23 passed at 100%. The SHA-256 hashes of all four test files are identical in both runs, and the characterization output is byte-for-byte identical. `manage.py check` is clean.
