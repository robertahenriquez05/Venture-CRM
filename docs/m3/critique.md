# M3 — Critique: AI First Draft vs. My Domain Model

## Summary
The AI's first draft (docs/m3/ai_first_draft.md) modelled 7 entities: USER,
ORGANIZATION, PIPELINE_STAGE, CONTACT, INTERACTION, FOLLOW_UP, TAG, and
CONTACT_TAG. My own model (docs/m3/my_domain_model.md) uses 4: CONTACT,
INTERACTION, TAG, and CONTACT_TAG. The difference comes down to over-modelling:
the AI turned three things that my requirements describe as simple attributes
into separate tables with foreign keys, and invented one ownership relationship
that isn't in my requirements at all.

## Over-modelled
1. **USER as a full entity.** The draft gave USER its own table with
   `username` and `password_hash` fields, plus an ownership foreign key
   (`user_id`) on every Contact. US-8 only requires that contact data be
   hidden behind a login — it says nothing about multiple users, roles, or
   contacts being scoped to an owner. Django's built-in auth system handles
   login/session state without needing to be represented as a domain entity.
   This is exactly the kind of default the assignment warns about: a User
   table appearing because it's a common pattern, not because a requirement
   asked for it.

2. **PIPELINE_STAGE as a separate table.** The draft modelled pipeline stage
   as its own entity with an `id`, `name`, and `sort_order`, linked to
   Contact by foreign key. US-2 specifies the stage is a dropdown of exactly
   six fixed values ("New Lead, Contacted, Meeting Scheduled, Warm,
   Committed, Cold") with no requirement that stages be added, edited, or
   carry their own attributes. That's a fixed `choices` field on Contact,
   not a table.

3. **ORGANIZATION as a separate table.** The draft linked Contact to
   Organization via foreign key. US-1 lists "organization" as one of several
   plain fields typed in when adding a contact, and US-7 says search should
   match organization name — neither implies organizations are managed
   records with their own lookups or attributes. A text field on Contact
   satisfies both stories.

## Under-modelled
No significant gaps. The AI's draft didn't miss any entity or relationship
that my requirements need — if anything it erred toward adding structure
rather than missing it.

## Guessed relationships with no basis
1. **FOLLOW_UP as its own table.** This implies a contact could have
   multiple follow-ups tracked over time (past and future). US-4 and US-5
   describe a single follow-up date per contact that gets set, displayed,
   flagged when overdue, and cleared — always in place on the same record,
   never as a list. There's no requirement asking for follow-up history.

2. **CONTACT → ORGANIZATION as a foreign-key relationship.** This assumes
   organizations are a shared, reusable entity that contacts point to. My
   requirements only describe organization as free text entered per contact
   (US-1), with no story about looking up or reusing an existing
   organization record.

## What it got right
1. **INTERACTION entity** — type, note (required text), and an
   auto-generated, non-editable timestamp match US-3 closely, including the
   detail that the timestamp isn't user-editable.
2. **TAG / CONTACT_TAG many-to-many** — correctly modelled tags as a
   separate entity with a join table, matching US-6's requirement that a
   contact can carry more than one tag from a fixed category list.
3. **CONTACT ↔ INTERACTION as one-to-many** — correctly identified that a
   contact can have multiple logged interactions (US-3's "3 logged
   interactions... listed in reverse chronological order").

## Why my model differs
I kept the model to 4 entities because every field and relationship in it
traces directly to a specific user story or NFR — CONTACT for US-1/US-2/
US-4/US-7, INTERACTION for US-3, and TAG/CONTACT_TAG for US-6. Stage,
follow-up date, and organization are single-value attributes on a contact
with no requirement suggesting they need their own table, history, or
lookup behavior. Adding tables for them would add migration complexity and
query joins with no corresponding benefit to any of the eight user stories.