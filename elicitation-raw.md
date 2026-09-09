# AI Elicitation — Raw Output (Evidence)

**Method:** To get an honest, unbiased elicitation, the prompt below was given
with *only* the one-line concept a stranger would have — no mention of the
solo/individual-course-project constraint, the demo-with-placeholder-data
plan, the specific pipeline categories (investor/mentor/regulatory), the
Django stack, or the eventual ThermalSense reuse. This is deliberate: those
details are exactly the kind of thing a real AI elicitation pass in the wild
would not have unless asked for, which is the point of the audit.

## Prompt given

> "I'm building a CRM web app — a lightweight tool for a solo startup
> founder to track contacts, pipeline stages, and follow-ups. Elicit
> requirements for this app: give me user stories with acceptance criteria,
> and non-functional requirements."

## Raw output received (verbatim, kept as evidence)

### User roles assumed
- **Admin** — full access, manages users and settings
- **Sales Rep** — manages their own contacts and deals
- **Manager** — views team-wide reporting across reps

### User stories

1. As a sales rep, I want to create and manage contact and company records
   (with linked deals), so that I can track every account I'm working.
   - AC: Given valid contact + company fields, when saved, a linked
     contact-company record is created.
   - AC: Given a company exists, when I add a new contact under it, then the
     contact inherits the company's industry/size fields by default.

2. As a sales rep, I want a Kanban-style pipeline board where I can drag
   deals between stages (Lead, Qualified, Proposal Sent, Negotiation, Won,
   Lost), so that I can visually manage my pipeline.
   - AC: Given a deal card, when I drag it to a new column, then its stage
     updates and the change is saved without a page reload.
   - AC: Given a deal is moved to "Won" or "Lost," then it is automatically
     time-stamped as closed.

3. As a sales rep, I want to sync my email inbox so sent/received messages
   with a contact appear automatically on their record, so that I don't have
   to log every email by hand.
   - AC: Given my email account is connected via OAuth, when I email a
     contact, then that message appears on their timeline within 5 minutes.

4. As a sales rep, I want to schedule tasks and reminders that notify me by
   email and push notification, so that I never miss a follow-up.
   - AC: Given a task with a due date/time, when that time arrives, then I
     receive both an email and a push notification.

5. As a manager, I want a reporting dashboard showing pipeline value,
   conversion rate by stage, and rep-by-rep performance, so that I can
   forecast revenue.
   - AC: Given deals with dollar values and stages, when I load the
     dashboard, then total pipeline value and stage-conversion percentages
     are calculated and displayed.

6. As an admin, I want to invite teammates and assign them roles
   (Admin/Manager/Rep) with different permission levels, so that I can
   control who sees what.
   - AC: Given I invite a user by email, when they accept, then they can log
     in with the role I assigned and see only the data that role permits.

7. As a sales rep, I want to import contacts from a CSV file and export my
   contact list at any time, so that I'm not locked into the platform.
   - AC: Given a CSV with mapped columns, when I upload it, then valid rows
     become contact records and invalid rows are reported with reasons.

8. As a sales rep, I want the app to work well on my phone, so that I can
   update deals between meetings.
   - AC: Given I load the app on a mobile browser, then all core flows
     (view pipeline, log activity, view contact) are usable without
     horizontal scrolling.

### Non-functional requirements suggested

- The system should have 99.9% uptime.
- The system should support up to 10,000 concurrent users without
  performance degradation.
- The system should be GDPR and CCPA compliant, including data export and
  right-to-deletion workflows.
- The system should scale horizontally to accommodate future growth.
- The system should encrypt data at rest and in transit.
- The system should provide daily automated backups with a 30-day retention
  window.
