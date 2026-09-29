No AI tools used to generate code on this milestone.

## M3: Domain Model and AI Critique

**Prompt used to generate AI first draft:**
"Here are my M2 requirements for Venture CRM (US-1 to US-8 and NFR-1 to
NFR-3): [full requirements.md pasted]. Draft a domain model as a Mermaid
erDiagram with entities, attributes, and cardinalities."

**Tool:** Claude (claude.ai chat)

**Output saved unedited as:** docs/m3/ai_first_draft.md

**What changed between the AI's draft and my own model:**
- Removed USER as a separate entity (no basis in requirements — US-8 is
  login/session security, not multi-user data modeling)
- Collapsed PIPELINE_STAGE from a separate table into a single `stage`
  field on Contact (US-2 specifies a fixed 6-value dropdown, not a
  growable/attributed entity)
- Collapsed ORGANIZATION from a separate table into a single `organization`
  field on Contact (US-1/US-7 only need a text field, not a managed lookup)
- Collapsed FOLLOW_UP from a separate table into a `follow_up_date` field
  on Contact (US-4/US-5 describe one follow-up date per contact, not a
  history of multiple follow-ups)
- Kept INTERACTION and TAG/CONTACT_TAG largely as the AI modeled them —
  both traced correctly to US-3 and US-6
- Full reasoning for each change is in docs/m3/critique.md

## IAP M4 — ADR-001 (2026-09-29)

**Tool:** Claude (claude.ai chat)

**Prompt:** Pasted the IAP M4 assignment text and asked Claude to help write ADR-001 for Venture CRM based on a real decision from my project.

**AI output:** A full draft of docs/adr/ADR-001-pipeline-stage-as-choices-field.md covering context, decision, three alternatives (PipelineStage table with FK, stage-change history table, free-text CharField), and consequences.

**Decision source:** The decision itself is mine, made during M3 when I rejected the AI draft's separate PIPELINE_STAGE table in favour of a fixed choices field on Contact (see docs/m3/critique.md). The ADR records that decision; it was not newly made by the AI.

**Diff / what I changed from the AI draft:**
- Reviewed the draft and accepted it as written.
