from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .management.commands.seed_demo import DEMO_CONTACTS
from .models import Contact, Interaction


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
        for _name, email, *_ in DEMO_CONTACTS:
            self.assertTrue(email.endswith("@example.com"), email)

    def test_demo_contacts_get_follow_ups_and_interactions(self):
        self.run_seed()
        self.assertEqual(Interaction.objects.count(), sum(len(row[5]) for row in DEMO_CONTACTS))
        self.assertTrue(Contact.objects.filter(follow_up_date__isnull=False).exists())

    def test_activity_is_added_to_demo_contacts_seeded_by_an_older_version(self):
        for name, email, company, stage, *_ in DEMO_CONTACTS:
            Contact.objects.create(name=name, email=email, company=company, stage=stage)
        output = self.run_seed()
        self.assertIn("Added demo follow-ups", output)
        self.assertEqual(Contact.objects.count(), len(DEMO_CONTACTS))
        self.assertGreater(Interaction.objects.count(), 0)

    def test_running_twice_does_not_duplicate_activity(self):
        self.run_seed()
        first = Interaction.objects.count()
        self.run_seed()
        self.assertEqual(Interaction.objects.count(), first)

    def test_contacts_the_user_edited_are_left_alone(self):
        self.run_seed("--reset")
        Interaction.objects.all().delete()
        maya = Contact.objects.get(email="maya.chen@example.com")
        maya.follow_up_date = None
        maya.save()
        Contact.objects.exclude(pk=maya.pk).update(follow_up_date="2030-01-01")
        self.run_seed()
        # Maya had no follow-up and no interactions, so she is enriched; the others had a follow-up set.
        self.assertTrue(Interaction.objects.filter(contact=maya).exists())
        self.assertEqual(Interaction.objects.exclude(contact=maya).count(), 0)
