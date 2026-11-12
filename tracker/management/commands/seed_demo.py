"""Load placeholder demo contacts (fake people, fake companies, example.com emails).

Used for class demos and the deployed site. Safe to run on every deploy:
- empty database: loads the demo contacts, their follow-ups and interactions;
- demo contacts already there (matched by their example.com email) with no follow-up and
  no interactions yet: adds those, so a site seeded by an older version gets them too;
- anything else is left alone. --reset wipes all contacts and loads the demo set again.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from tracker.models import Contact, Interaction

S = Contact.Stage
K = Interaction.Kind

# name, email, company, stage, follow-up (days from today, or None), interactions (oldest first)
DEMO_CONTACTS = [
    ("Maya Chen", "maya.chen@example.com", "Northline Ventures", S.COMMITTED, 14, [
        (K.MEETING, "Partner meeting went well. Asked for the data room link and two customer references."),
        (K.EMAIL, "Sent data room access and references. She confirmed a $50k commitment pending paperwork."),
    ]),
    ("David Okafor", "d.okafor@example.com", "Bluff City Angels", S.MEETING_SCHEDULED, 0, [
        (K.EMAIL, "Intro from a mutual advisor. Interested in health-tech pre-seed."),
        (K.CALL, "15-minute screening call. Booked a full pitch with the group for next week."),
    ]),
    ("Priya Raman", "priya@example.com", "MedDevice Advisors", S.CONTACTED, -3, [
        (K.EMAIL, "Reached out about FDA pathway advice for a Class II device. Waiting on a reply."),
    ]),
    ("Luis Ortega", "luis.ortega@example.com", "Riverside Accelerator", S.NEW_LEAD, 5, []),
    ("Hannah Brooks", "hbrooks@example.com", "Delta Health Partners", S.WARM, 2, [
        (K.MEETING, "Coffee at the innovation hub. Open to a pilot at two clinics if pricing works."),
        (K.CALL, "Walked through pilot pricing. She'll take it to her ops lead."),
    ]),
    ("Marcus Webb", "marcus.webb@example.com", "Summit Seed Fund", S.COLD, None, [
        (K.CALL, "Passed for now: too early for their fund. Said to check back after first revenue."),
    ]),
    ("Elena Rossi", "elena.rossi@example.com", "Regulatory Path Consulting", S.MEETING_SCHEDULED, 9, [
        (K.EMAIL, "Scheduled a working session on the regulatory roadmap."),
    ]),
    ("Tom Nguyen", "tom@example.com", "University Tech Transfer", S.CONTACTED, -1, [
        (K.CALL, "Discussed licensing terms for the university IP. Sending the term sheet draft."),
    ]),
]


class Command(BaseCommand):
    help = "Load placeholder demo contacts (with follow-ups and interactions) if they are not there yet."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete all contacts first, then load demo data.")

    def handle(self, *args, **options):
        if options["reset"]:
            Contact.objects.all().delete()
        if not Contact.objects.exists():
            # Oldest first, so the list (newest first) shows the last one at the top.
            for name, email, company, stage, *_ in DEMO_CONTACTS:
                Contact.objects.create(name=name, email=email, company=company, stage=stage)
            self.stdout.write(self.style.SUCCESS(f"Loaded {len(DEMO_CONTACTS)} demo contacts."))
        else:
            self.stdout.write("Contacts already exist; demo contacts not loaded.")
        enriched = self.add_demo_activity()
        if enriched:
            self.stdout.write(self.style.SUCCESS(f"Added demo follow-ups and interactions to {enriched} contacts."))

    def add_demo_activity(self):
        """Give untouched demo contacts a follow-up and a believable history spread over the past weeks."""
        now = timezone.now()
        today = timezone.localdate()
        enriched = 0
        for index, (_name, email, _company, _stage, follow_up_in, interactions) in enumerate(DEMO_CONTACTS):
            contact = Contact.objects.filter(email=email).first()
            if contact is None or contact.follow_up_date or contact.interactions.exists():
                continue
            # First demo contact was "added" ~4 weeks ago, the last ~4 days ago (keeps newest-first order).
            added = now - timedelta(days=28 - 3 * index, hours=index)
            contact.created_at = added
            contact.follow_up_date = today + timedelta(days=follow_up_in) if follow_up_in is not None else None
            contact.save(update_fields=["created_at", "follow_up_date"])
            step = (now - added) / (len(interactions) + 1)
            for position, (kind, note) in enumerate(interactions, start=1):
                interaction = Interaction.objects.create(contact=contact, kind=kind, note=note)
                Interaction.objects.filter(pk=interaction.pk).update(created_at=added + step * position)
            enriched += 1
        return enriched
