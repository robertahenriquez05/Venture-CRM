"""Load placeholder demo contacts (fake people, fake companies, example.com emails).

Used for class demos and the deployed site. Safe to run on every deploy: it does
nothing if the database already has contacts, unless --reset is passed.
"""

from django.core.management.base import BaseCommand

from tracker.models import Contact

DEMO_CONTACTS = [
    ("Maya Chen", "maya.chen@example.com", "Northline Ventures", Contact.Stage.ACTIVE),
    ("David Okafor", "d.okafor@example.com", "Bluff City Angels", Contact.Stage.MEETING),
    ("Priya Raman", "priya@example.com", "MedDevice Advisors", Contact.Stage.CONTACTED),
    ("Luis Ortega", "luis.ortega@example.com", "Riverside Accelerator", Contact.Stage.LEAD),
    ("Hannah Brooks", "hbrooks@example.com", "Delta Health Partners", Contact.Stage.ACTIVE),
    ("Marcus Webb", "marcus.webb@example.com", "Summit Seed Fund", Contact.Stage.DORMANT),
    ("Elena Rossi", "elena.rossi@example.com", "Regulatory Path Consulting", Contact.Stage.MEETING),
    ("Tom Nguyen", "tom@example.com", "University Tech Transfer", Contact.Stage.CONTACTED),
]


class Command(BaseCommand):
    help = "Load placeholder demo contacts if the database is empty."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete all contacts first, then load demo data.")

    def handle(self, *args, **options):
        if options["reset"]:
            Contact.objects.all().delete()
        if Contact.objects.exists():
            self.stdout.write("Contacts already exist; demo data not loaded.")
            return
        # Oldest first, so the list (newest first) shows the last one at the top.
        for name, email, company, stage in DEMO_CONTACTS:
            Contact.objects.create(name=name, email=email, company=company, stage=stage)
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(DEMO_CONTACTS)} demo contacts."))
