# ADR-001: Store pipeline stage as a fixed choices field on Contact, not a separate table

**Status:** Accepted
**Date:** 2026-09-21 (decided during M3 domain modelling); recorded 2026-09-29
**Author:** Roberta Henriquez Fassio

## Context

Venture CRM tracks where each founder relationship stands. US-2 requires that
every contact be assigned exactly one pipeline stage, chosen from a dropdown of
six fixed values: New Lead, Contacted, Meeting Scheduled, Warm, Committed, and
Cold. US-5 (follow-up dashboard) and US-7 (search) both read contacts in bulk,
and NFR-1 sets a performance expectation for those list views.

When I asked an AI tool to draft the domain model in M3, it modelled
`PIPELINE_STAGE` as its own table (`id`, `name`, `sort_order`) linked to
`CONTACT` by foreign key. That is a common CRM pattern and a reasonable
default, so I had to decide deliberately whether this app needs it.

The forces pulling in different directions:

- **Fixed vs. flexible.** My requirements say the six stages are fixed. But
  after the semester I plan to use this app for real contacts, and a real
  fundraising pipeline could need different stages later.
- **Simplicity.** This is a single-user app built by one developer on a
  semester timeline. Every extra table means another model, migration, admin
  screen, seed-data step, and join in every list query.
- **Data integrity.** Stage values must be valid and consistent so filtering
  and the dashboard work. Free text would break that.
- **History.** Nothing in M2 asks when a contact changed stages, but a CRM is
  the kind of app where someone eventually asks that question.

## Decision

Pipeline stage is stored as a single `CharField` on the `Contact` model,
restricted to a Django `TextChoices` enumeration of the six values in US-2.
Each contact holds only its current stage. There is no `PipelineStage` table
and no stage-change history.

```python
class Contact(models.Model):
    class Stage(models.TextChoices):
        NEW_LEAD = "new_lead", "New Lead"
        CONTACTED = "contacted", "Contacted"
        MEETING_SCHEDULED = "meeting_scheduled", "Meeting Scheduled"
        WARM = "warm", "Warm"
        COMMITTED = "committed", "Committed"
        COLD = "cold", "Cold"

    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.NEW_LEAD,
    )
```

## Alternatives considered

### 1. Separate `PipelineStage` table with a foreign key from `Contact`
This is what the AI draft proposed. It would let stages be added, renamed, or
reordered through the admin with no code change, and each stage could carry
its own attributes (sort order, colour, description).

**Why not chosen:** US-2 states the six stages are fixed, and no requirement
asks to edit stages or give them attributes. The table would add a model, a
migration, an admin screen, a seed step that must run before any contact can
be created, a join on every dashboard and search query, and an `on_delete`
decision (what happens to contacts if a stage row is deleted). All of that
cost buys flexibility that no user story asks for.

### 2. Stage-change history table (`StageChange` event log)
Record every stage transition as a row (`contact`, `from_stage`, `to_stage`,
`changed_at`) and derive the current stage from the latest row. This would
answer "when did this contact become Warm?" and support funnel reporting.

**Why not chosen:** No M2 requirement asks for stage history or time-in-stage.
Deriving the current stage from the latest event means a subquery or
denormalized cache on every list view, which works against NFR-1 and adds
complexity to US-5 and US-7 for no requirement that uses it. The Interaction
log (US-3) already gives me a free-text record of what happened with each
contact.

### 3. Plain `CharField` with no choices constraint
Simplest possible option: store whatever string is typed.

**Why not chosen:** US-2 explicitly requires a dropdown of fixed values.
Free text would allow typos and inconsistent casing ("warm", "Warm ",
"WARM"), which would silently break stage filtering and the dashboard.

## Consequences

### What this makes easier
- The model stays at four entities, matching the M3 domain model.
- Stage filtering and the dashboard query a single table with no join.
- Django validates stage values automatically, and the dropdown in forms and
  the admin is generated from the choices with no extra code.
- Seed/demo data is simpler: contacts can be created without first
  populating a lookup table.

### What this makes harder (doors this closes)
- **Changing the stages requires a code change and a migration.** Adding a
  seventh stage (for example "Due Diligence" once I use this for real
  fundraising) means editing `Contact.Stage`, running `makemigrations`, and
  redeploying. It cannot be done from the admin or by a non-developer.
- **Renaming or removing a stage needs a data migration.** Existing rows
  store the key (`"warm"`), not a reference. If I rename or delete a key,
  rows holding the old value become invalid and must be updated by a
  hand-written data migration, or they will fail validation the next time
  they are edited.
- **No stage history exists, and it cannot be recovered later.** Because only
  the current stage is stored, I cannot answer "when did this contact move to
  Committed?" or measure time spent in each stage. If I add a history table
  later, it will only contain transitions from that point forward; every
  change before it is lost for good.
- **No per-stage attributes.** Display order, colours, or descriptions for
  stages must live in code (the order of the `TextChoices` class), not in
  data.
- **One pipeline for every kind of contact.** Investors, mentors, and advisors
  all share the same six stages. Supporting a different pipeline per contact
  type would require restructuring into something like Alternative 1.

### When to revisit
Revisit this decision if stages need to change more than about once a
semester, if a non-developer needs to edit them, or if any requirement asks
for stage history or funnel reporting. At that point, migrating to
Alternative 1 and/or Alternative 2 is the expected path.
