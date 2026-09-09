# Prompt-and-Diff Log

## Prompts used

**Prompt 1 (elicitation — deliberately minimal, no project-specific context):**
> "I'm building a CRM web app — a lightweight tool for a solo startup founder
> to track contacts, pipeline stages, and follow-ups. Elicit requirements for
> this app: give me user stories with acceptance criteria, and non-functional
> requirements."
→ Output: `elicitation-raw.md` (kept verbatim, unedited).

**Prompt 2 (asked with full project context, to produce the real
requirements document):**
> "Now, with full context — this is my individual Software Engineering
> course project (Venture CRM / Founder HQ), solo user only, Django, demoed
> with placeholder data, pipeline categories are investor/mentor/technical
> connector/regulatory — write the real requirements doc: 6-8 user stories
> with acceptance criteria in Given/When/Then format, and 3 non-functional
> requirements each stated as a falsifiable number/threshold/condition."
→ Output: `requirements.md`.

## Diff: raw AI output → final adopted requirements

| # | Raw AI story/NFR | Disposition | Final version |
|---|---|---|---|
| 1 | Contact+company records, inherits company fields | **Rewritten** — dropped company-inheritance, kept "single contact record" core | US-1: add contact with name/org/role/email/phone/how-we-met, with duplicate-email warning |
| 2 | Kanban drag-and-drop pipeline board, generic sales stages | **Rewritten** — dropped drag-and-drop UI, replaced stage vocabulary | US-2: dropdown-based stage field, 6 relationship-specific stages, defaults to "New Lead" |
| 3 | Email inbox OAuth sync, auto-logs messages | **Rejected** — out of scope, not feasible in course timeline | US-3: manual interaction log with type + note, auto-timestamped, reverse-chronological |
| 4 | Task/reminder with email + push notification | **Rewritten** — dropped notification infra | US-4: follow-up date field on contact, no external notification channel |
| 5 | Manager reporting dashboard (pipeline value, conversion %, rep performance) | **Rewritten** — dropped sales-KPI framing entirely | US-5: dashboard = list of contacts with follow-up due today/overdue |
| 6 | Admin invites teammates, role-based permissions | **Rejected** — no team exists | Replaced with US-8: single-user password-protected login |
| 7 | CSV import/export | **Accepted, deferred** — good idea, not in this milestone's 6-8 stories | Noted in audit as a fast-follow; not included as a graded story to keep scope honest |
| 8 | Mobile responsiveness as hard requirement | **Rejected** — not requested, not a course-project priority | Not carried forward |
| — | *(new, not from AI)* | **Added** | US-6: tag/filter by contact category (investor/mentor/connector/regulatory) |
| — | *(new, not from AI)* | **Added** | US-7: search by name/organization |
| NFR | 99.9% uptime | **Rejected** — no infra to guarantee this, unverifiable in course grading | Not carried forward |
| NFR | 10,000 concurrent users | **Rejected** — single user, meaningless | Not carried forward |
| NFR | GDPR/CCPA compliance workflows | **Rejected** — out of scope for placeholder-data class project | Not carried forward |
| NFR | Horizontal scalability | **Rejected** — no basis; single user | Not carried forward |
| NFR | Encrypt data at rest/in transit | **Deferred** — reasonable for real data later, not independently gradable now | Not carried forward as a graded NFR; flagged in audit |
| NFR | Daily backups, 30-day retention | **Rejected** — no infra to support this claim | Not carried forward |
| — | *(new, not from AI)* | **Added** | NFR-1: contact list renders ≤ 2s for 500 contacts (3 runs, DevTools-measured) |
| — | *(new, not from AI)* | **Added** | NFR-2: 0 of 6 contact-data endpoints return data to an unauthenticated request |
| — | *(new, not from AI)* | **Added** | NFR-3: 0 of 10 test contacts show a mismatched follow-up date/stage after logout/login |

## Summary

Of the AI's 8 stories: 0 adopted unchanged, 4 rewritten to fit the real
single-user scope, 3 rejected outright, 1 accepted-but-deferred. Of its 6
NFRs: 0 adopted, 1 deferred as a future concern, 5 rejected as inapplicable
boilerplate. All 3 final NFRs and 2 of the final 8 stories were authored
from scratch because the AI pass never surfaced them.
