# AI Elicitation Audit Log

Comparing the raw AI output (`elicitation-raw.md`) against the actual
requirements for Venture CRM (`requirements.md`).

## What the model missed (never asked about)

1. **Who the user actually is.** It never asked "is this for one person or a
   team?" and defaulted to a 3-role, multi-tenant sales org (Admin/Manager/
   Rep). Venture CRM has exactly one user. This single wrong assumption is
   what caused most of the downstream over-scoping below — it's a
   requirements-elicitation failure, not just a feature miss.
2. **The actual pipeline vocabulary.** It invented generic sales-funnel
   stages (Lead → Qualified → Proposal Sent → Negotiation → Won/Lost)
   instead of asking what stages matter for *this* relationship-tracking use
   case (New Lead, Contacted, Meeting Scheduled, Warm, Committed, Cold). It
   never asked what "pipeline" meant in context — it assumed B2B sales.
3. **Why data sensitivity matters here.** It never asked whether the data
   would be real or fake, or who else could see the repo — relevant because
   the app is being demoed in class with placeholder data and a professor is
   a repo collaborator. This is why access control (NFR-2) needed to be
   explicit and testable, not generic "encrypt data" language.
4. **The tech/deployment constraints.** It never asked what stack this runs
   on (Django) or where it's hosted, which is exactly why its performance and
   uptime NFRs are unmoored from reality (see inventions below).
5. **The contact categories that actually matter to a founder** — investor,
   mentor, technical connector, regulatory/FDA contact. It offered "company/
   industry/size" fields, which are B2B-sales fields, not founder-network
   fields.

## What it invented (that was never wanted)

1. **Multi-user roles and an invite/permissions system (story 6).** There is
   no team. This single invented requirement would have added an entire
   authentication/authorization subsystem to a one-person class project.
2. **Email inbox sync via OAuth (story 3).** Not asked for, not feasible to
   build/grade in a course timeline, and not something the actual workflow
   needs — interactions are logged manually and deliberately (US-3), not
   auto-captured.
3. **Drag-and-drop Kanban board (story 2).** A visual nicety that was
   invented as the interaction model, when the real need is just an editable
   stage field per contact (US-2). Committing to drag-and-drop would have
   meant building real-time reordering logic for no benefit.
4. **Push notifications (story 4).** Assumes a mobile app or browser-push
   infrastructure that doesn't exist and wasn't requested; the actual need
   (US-4/US-5) is satisfied by a "due today/overdue" list on login.
5. **Revenue/conversion-rate reporting dashboard (story 5).** This is a
   sales-team KPI feature. A founder tracking mentors and investors has no
   "deal value" or "conversion rate" to report on.
6. **Enterprise-grade NFRs with no basis:** 99.9% uptime, 10,000 concurrent
   users, horizontal scalability, GDPR/CCPA compliance workflows. All six are
   generic SaaS boilerplate copied from a template, not requirements derived
   from this app. A single-user Django app graded in a course has zero
   concurrent-user problem and no EU/CA data subjects to serve rights to.
7. **Native mobile responsiveness as a hard requirement (story 8).** Never
   requested; not worth the scope for a class project demo.

## What it got right (that hadn't been thought of yet)

1. **CSV import/export.** Not in the original plan, but genuinely useful:
   it gives a real path for the planned switch from placeholder demo data to
   real ThermalSense-related contacts after the course ends, and doubles as
   a backup. Worth adding as a fast-follow after the graded milestone.
2. **Deals/records "inheriting" fields from a linked parent record.** The
   specific implementation (contact inherits company fields) doesn't apply,
   but the underlying idea — reduce repeated data entry when contacts share
   an organization — is legitimate and could simplify adding, e.g., two
   contacts from the same VC firm.
3. **Encryption and backups as a category worth naming**, even though its
   specific claims were boilerplate. It's a fair prompt to double-check: the
   final NFRs (this doc's companion `requirements.md`) intentionally still
   don't commit to encryption-at-rest as a course-project NFR, since it's not
   independently verifiable in the time available — but it's flagged here as
   a reasonable real-world follow-up once real contact data goes in.

## Judgment

The model did not fail at writing — the prose, the Given/When/Then shape,
and the structure were all competent. It failed at *elicitation*: given a
one-line prompt, it should have asked at least "solo or team?" and "what do
your pipeline stages mean here?" before generating eight stories. Instead it
pattern-matched "CRM" to the most common CRM shape it has seen (multi-user
B2B sales tool) and produced a requirements set for a different product than
the one being built. About five of its eight stories and five of its six
NFRs describe features or constraints this project should explicitly *not*
build. That is the core lesson of this audit: a generated requirements list
reads as thorough and professional, but "thorough-sounding" and "correct for
this app" are different properties, and only a founder who already knows
what they're building can tell the two apart. The two genuinely useful ideas
it surfaced (CSV import/export, reduced re-entry for shared-organization
contacts) came from generic CRM-domain knowledge, not from anything specific
to this app — which is exactly the kind of contribution AI elicitation is
good for, and exactly why it still needs a human audit before being trusted.
