# IAP M7 - Documented Refactor

**Refactored:** `tracker/views.py` (the `contact_list` view, the only view in the app).
**Not changed:** every test file, the URL config, the template, the model, the form.

## 1. What was wrong (the smell)

**Smell: Divergent Change inside a fall-through conditional.** One view function did two unrelated jobs, *showing the contact list* and *creating a contact*. The two jobs were tangled together through a shared `form` variable:

```python
def contact_list(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("contact_list")
        # invalid POST does NOT return here; it falls out of the if ...
    else:
        form = ContactForm()

    contacts = Contact.objects.all()          # ... and lands in code written for GET
    return render(request, "tracker/contact_list.html", {"form": form, "contacts": contacts})
```

The page has three outcomes: a blank page, a redirect after a successful save, and the page re-shown with errors. Only two of them had their own `return`. The third, "invalid submission", had no line of its own. It worked only because control fell through into the list-building code at the bottom. So the create path depended on the list path without saying so. Any change to how the list is built (search, filters, the follow-up "due" badge) would also change what an invalid submission shows, and nothing in the code warned you about that.

It also fails the "one reason to change" test. US-1 (redirect to a detail page, duplicate-email warning), US-6 (filter by category), and US-7 (search) are all in `requirements.md`, and each one would have meant editing this same function and adding more branches to the same `if`.

## 2. What I did

I used Extract Function three times, and turned the fall-through into explicit returns:

| New function | Its one job |
|---|---|
| `contact_list(request)` | Entry point for `/`. Only dispatches: POST goes to `add_contact`, everything else goes to `show_contact_page`. |
| `add_contact(request)` | Validate and save. A guard clause sends an invalid form back to the page; a valid one is saved and redirected. |
| `show_contact_page(request, form)` | Render the page around whatever form it is given (blank, or carrying errors). |
| `contacts_for_list()` | The single place that decides which contacts the list shows. |

Each of the three outcomes is now one visible `return`. The template name is a named constant instead of a string buried in a call.

Kept identical on purpose: the view's name and URL (`reverse("contact_list")` and `tracker/urls.py` are untouched), the template, and the HTTP behaviour for every request type.

Diff: [`refactor.diff`](refactor.diff)

## 3. Proof that behaviour did not change

| Evidence | Before | After |
|---|---|---|
| Full suite (`coverage run manage.py test --verbosity 2`) | [`before_test_output.txt`](before_test_output.txt): **23 tests, OK** | [`after_test_output.txt`](after_test_output.txt): **23 tests, OK** |
| Coverage | 100% statements and branches | 100% statements and branches |
| Characterization check ([`characterize.py`](characterize.py)) | [`before_characterization.txt`](before_characterization.txt) | [`after_characterization.txt`](after_characterization.txt): **byte-for-byte identical** |

**The test set was not changed between runs.** The header of each test-output file lists the SHA-256 hash of all four test files (`tests.py`, `test_acceptance.py`, `test_forms.py`, `test_models.py`). The hashes are identical in both files, and both runs list the same 23 test names in the same order. Only the hash of `tracker/views.py` differs.

**Why the extra characterization check:** the suite only sends GET and POST. Before refactoring, I wanted to know what the view does with requests nobody tests. The script sends GET, HEAD, valid and invalid POSTs, PUT and DELETE, and records the status code, redirect target, number of rows in the database, and a hash of each page (with the CSRF token and timestamps blanked out). Running it before and after gives identical output.

It also surfaced one existing quirk that I deliberately did **not** fix. PUT and DELETE to `/` return the list page with status 200, because the old `else` branch treated every non-POST request as GET. The refactor keeps that exactly (`contact_list` still sends every non-POST to `show_contact_page`). Changing it to a 405 would be a behaviour change, so it belongs in a feature or bug-fix commit with its own test, not in a refactor.

## 4. What is now easier, and why

- **Adding search (US-7) or category filters (US-6):** edit `contacts_for_list()` only. The normal page and the "invalid submission" page both call `show_contact_page`, which calls `contacts_for_list`, so they cannot drift apart. Before, you had to know that the invalid-POST path silently fell through into the list code.
- **Changing what happens after a save** (US-1 wants a redirect to the new contact's detail page, plus a duplicate-email warning): edit `add_contact()` only. The list code is no longer in the same function, so it can't be broken by accident.
- **Reading the view:** each outcome (blank page, redirect, page with errors) is one `return` line. You no longer have to trace which branch assigned `form` before the shared code at the bottom.
- **Adding a second page later** (detail page, dashboard): the pattern is set. The entry point dispatches, small functions do one job each, and the query lives in one named place.

## How to reproduce

```
python -m coverage run manage.py test --verbosity 2    # after: 23 tests, OK
python docs/m7/characterize.py                         # matches after_characterization.txt
git checkout HEAD~1 -- tracker/views.py               # temporarily put the OLD view back
python -m coverage run manage.py test --verbosity 2    # before: 23 tests, OK
python docs/m7/characterize.py                         # matches before_characterization.txt
git checkout HEAD -- tracker/views.py                  # bring the refactor back
```
