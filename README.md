# Venture-CRM
Venture-CRM is a lightweight web app for tracking early-stage founder relationships; advisors, mentors, and investor contacts, along with where each relationship stands and what follow-up is needed next. Built for solo founders who don't need a full-scale CRM, just a simple way to keep track of who they've talked to and what's pending. Built with Python and Django.

## Logging and runbooks

The app writes structured JSON logs (one object per line) to the terminal and to `logs/venture-crm.jsonl`. Every request gets a `request_id` that appears on all of its log lines, in the `X-Request-ID` response header, and as the "Reference code" on the error page.

- Read the log: `python scripts/logq.py --failed`, `python scripts/logq.py <request_id>`, `python scripts/logq.py --last 20`
- Field reference and a traced example: [`docs/m8/README.md`](docs/m8/README.md)
- Runbooks: [`RB-001: "Add contact" shows an error page`](docs/runbooks/RB-001-add-contact-error-page.md)
