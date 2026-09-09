# Venture CRM (Founder HQ) — Requirements Document

**IAP M2 — Requirements and AI Elicitation Audit**
Author: Roberta Henriquez
Repository: github.com/robertahenriquez05/Venture-CRM

## App concept

Venture CRM is a lightweight, single-user web application (Django) that lets a solo
startup founder track the contacts, pipeline status, and follow-ups involved in
building a company — investors, mentors, technical connectors, and regulatory
contacts. It is being built as an individual software engineering course project,
demoed with placeholder data, and intended for real use afterward.

## User stories

Format for every story:

> **US-#: As a `<role>`, I want to `<goal>`, so that `<benefit>`.**
> Acceptance criteria are written as Given/When/Then and are meant to be checked
> off individually — each is a pass/fail statement, not a description.

---

**US-1: As a founder, I want to add a new contact with name, organization, role,
email, phone, and how we met, so that I have a single record for every person in
my network.**

- Given I am on the "Add Contact" form, when I submit valid values for name and
  email (the only required fields), then a new contact record is created and I
  am redirected to that contact's detail page.
- Given I submit the form with the name or email field empty, when I click
  Save, then the form re-renders with an inline error on the missing field and
  no record is created.
- Given I submit an email address that already exists on another contact, when
  I click Save, then I see a warning ("possible duplicate") but am still
  allowed to save.

**US-2: As a founder, I want to assign a pipeline stage to each contact (New
Lead, Contacted, Meeting Scheduled, Warm, Committed, Cold), so that I can see
where each relationship stands at a glance.**

- Given a contact exists, when I open their detail page, then their current
  stage is visible and editable via a dropdown of exactly those six values.
- Given I change a contact's stage and save, when I return to the contact
  list, then the list reflects the new stage without a page-cache refresh
  needed.
- Given a contact has never had a stage set, when it is created, then it
  defaults to "New Lead."

**US-3: As a founder, I want to log interactions (call, email, meeting) with a
timestamped note on a contact's record, so that I can recall context before
reaching out again.**

- Given I am on a contact's detail page, when I submit an interaction with a
  type and a note, then it appears at the top of that contact's interaction
  timeline with an auto-generated timestamp (not user-editable).
- Given a contact has 3 logged interactions, when I view their detail page,
  then all 3 are listed in reverse chronological order.
- Given I submit an interaction with no note text, when I click Save, then the
  form rejects it with an inline error and nothing is logged.

**US-4: As a founder, I want to set a follow-up reminder date on a contact, so
that I don't let promising relationships go cold.**

- Given a contact's detail page, when I set a follow-up date in the future and
  save, then that date is stored and displayed on the contact card.
- Given a contact's follow-up date is today or earlier, when I view the
  contact list, then that contact is visually flagged (e.g., a "due" badge).
- Given I clear a follow-up date, when I save, then the contact no longer
  appears in the "due" list.

**US-5: As a founder, I want a dashboard listing contacts with follow-ups due
today or overdue, so that I know exactly who to reach out to each day.**

- Given at least one contact has a follow-up date ≤ today, when I load the
  dashboard, then that contact appears in a "Due" section sorted oldest date
  first.
- Given no contacts have a follow-up due, when I load the dashboard, then the
  "Due" section displays an explicit empty state, not a blank space.
- Given I resolve a follow-up (log an interaction or push the date forward),
  when I reload the dashboard, then that contact no longer appears in "Due."

**US-6: As a founder, I want to tag contacts by category (investor, mentor,
technical connector, regulatory/FDA, other), so that I can filter my network
by type when I need a specific kind of help.**

- Given a contact's detail page, when I assign one or more tags from the fixed
  category list and save, then those tags display on the contact's card in
  the list view.
- Given at least one contact is tagged "investor," when I filter the contact
  list by "investor," then only contacts with that tag are shown.
- Given a contact has zero tags, when I filter by any category, then that
  contact is excluded from the results.

**US-7: As a founder, I want to search contacts by name or organization, so
that I can quickly find the right person among many records.**

- Given a contact named "Josh Bush" exists, when I type "josh" into the search
  box, then his record appears in the filtered results within the same page
  (no full reload).
- Given no contact matches the search term, when I search, then an explicit
  "No contacts found" message displays instead of an empty table.
- Given a search term matches an organization name but not any contact's
  name, when I search, then contacts from that organization still appear.

**US-8: As a founder, I want to log in with a password-protected account, so
that my contact data — even placeholder demo data — isn't publicly viewable.**

- Given I am not logged in, when I request any contact list or detail URL
  directly, then I am redirected to the login page instead of seeing the
  data.
- Given I enter valid credentials on the login page, when I submit, then I am
  redirected to the dashboard and my session persists across page loads.
- Given I enter an incorrect password 3 times in a row, when I submit the 3rd
  attempt, then I see a generic "invalid credentials" error that does not
  reveal whether the username existed.

## Non-functional requirements

Each NFR below is written so it can be checked and either pass or fail — a
number, threshold, or named condition, not a vague quality.

**NFR-1 (Performance):** The contact list view SHALL fully render (all
network requests complete, DOM interactive) in ≤ 2 seconds for a database of
500 contacts, measured via browser DevTools Network/Performance panel over 3
consecutive page loads on a connection of ≥ 10 Mbps.

**NFR-2 (Access control):** Every contact-data endpoint (contact list,
contact detail, add/edit/delete contact, interaction log, dashboard — 6
endpoints total) SHALL reject an unauthenticated request with an HTTP 302
redirect to `/login/` or an HTTP 401/403 response. Verified by requesting each
endpoint directly, while logged out, using curl or the browser in a private
window: 0 of 6 may return contact data.

**NFR-3 (Data integrity):** A follow-up date or pipeline stage saved on a
contact SHALL be retrievable unchanged after logout and re-login. Verified
against 10 test contacts: after setting a distinct date/stage on each,
logging out, logging back in, and reloading each contact, 0 of 10 may show a
mismatched value.
