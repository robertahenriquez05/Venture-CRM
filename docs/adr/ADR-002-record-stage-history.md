# ADR-002: Record pipeline-stage history in an append-only StageChange table

**Status:** Accepted (2026-11-12). Amends ADR-001: keeps its decision, replaces its "no history" consequence.

## Context

ADR-001 stores a contact's current stage as a fixed `TextChoices` field on `Contact`. One of its listed
consequences was that **stage history is not recorded**, and that adding it later would start empty.

Preparing the design defense made the cost of that consequence clearer. The two "harder" consequences
of ADR-001 are not the same kind of cost:

- Moving stages into their own table later is **reversible**: a schema migration and a data migration.
- History not recorded today is **irreversible**: nothing can reconstruct when a contact moved from
  Warm to Committed if the app never wrote it down.

For a founder CRM, "how long has this investor been at Warm?" is one of the questions the tool exists
to answer once it holds real contacts. ADR-001 weighed the two costs as if they were equal.

## Decision

Keep ADR-001's current-stage field exactly as it is, and **also** append one `StageChange` row
(`contact`, `from_stage`, `to_stage`, `changed_at`) every time a contact's stage is set or changes.

- History is written in one place: `Contact.save()`, inside the same transaction as the row update.
  Every write path in the app (add form, edit form, pipeline board, admin) goes through `save()`.
- The table is append-only: the admin shows it read-only and the app never edits or deletes rows
  (they are only removed with their contact, by `on_delete=CASCADE`).
- The list page and the pipeline board never read it. Only the contact detail page does
  ("Stage history", and "In Warm for 5 days").
- No backfill. Contacts that existed before migration `0004` have no history, and the detail page says
  "since before stage history was recorded" rather than inventing a date.

## Alternatives considered

1. **Leave it as ADR-001 decided (no history).** Zero cost now, but every day without it is history
   lost for good. Rejected for the reason in Context.
2. **Alternative B from ADR-001: derive the current stage from the latest event.** Gives history, but
   every list and board read needs a subquery, and the current stage now lives in two places' logic.
   Rejected; this ADR keeps the current stage on the row, so reads do not change.
3. **A generic audit log of every field change** (e.g. a package such as django-simple-history).
   Records much more than any story asks for and adds a dependency. Rejected for now.

## Consequences

- **Easier:** time-in-stage and the path a contact took are visible on the detail page; funnel reports
  (how long contacts take from Contacted to Committed) become possible later.
- **Reads unaffected:** the list and board still query one table (NFR-1 argument from ADR-001 holds).
- **One extra query per save** to read the previous stage. Acceptable for a single-user app.
- **Known gap:** `QuerySet.update()` and raw SQL bypass `save()` and would change a stage without
  history. Nothing in the app does that; the demo seed script writes history explicitly. A database
  trigger would close the gap but is not worth it at this size.
- **Still true from ADR-001:** adding or renaming a stage is a code change plus migration. Existing
  `StageChange` rows store stage keys, so a rename now needs its data migration to update this table too.
