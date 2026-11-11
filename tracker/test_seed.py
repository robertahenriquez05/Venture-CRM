from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .management.commands.seed_demo import DEMO_CONTACTS
from .models import Contact


class SeedDemoCommandTests(TestCase):
    def run_seed(self, *args):
        out = StringIO()
        call_command("seed_demo", *args, stdout=out)
        return out.getvalue()

    def test_loads_demo_contacts_into_empty_database(self):
        output = self.run_seed()
        self.assertEqual(Contact.objects.count(), len(DEMO_CONTACTS))
        self.assertIn("Loaded", output)

    def test_does_not_touch_existing_contacts(self):
        Contact.objects.create(name="Real Person")
        output = self.run_seed()
        self.assertEqual(list(Contact.objects.values_list("name", flat=True)), ["Real Person"])
        self.assertIn("already exist", output)

    def test_reset_replaces_existing_contacts(self):
        Contact.objects.create(name="Old Row")
        self.run_seed("--reset")
        self.assertEqual(Contact.objects.count(), len(DEMO_CONTACTS))
        self.assertFalse(Contact.objects.filter(name="Old Row").exists())

    def test_demo_data_uses_only_placeholder_emails(self):
        for _name, email, _company, _stage in DEMO_CONTACTS:
            self.assertTrue(email.endswith("@example.com"), email)
