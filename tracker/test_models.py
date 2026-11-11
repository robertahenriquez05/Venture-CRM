"""
M6 unit tests for the Contact model: defaults, display, and the order
contacts come back from the database (which is the order the list page shows).
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Contact


class ContactModelTests(TestCase):
    def test_new_contact_starts_in_the_new_lead_stage(self):
        contact = Contact.objects.create(name="Jane Demo")
        self.assertEqual(contact.stage, "new_lead")

    def test_creation_time_is_recorded_automatically(self):
        before = timezone.now()
        contact = Contact.objects.create(name="Jane Demo")
        after = timezone.now()
        self.assertTrue(before <= contact.created_at <= after)

    def test_contact_is_shown_by_its_name(self):
        self.assertEqual(str(Contact(name="Jane Demo")), "Jane Demo")

    def test_stage_is_displayed_with_its_human_readable_label(self):
        expected = {
            "new_lead": "New Lead",
            "contacted": "Contacted",
            "meeting_scheduled": "Meeting Scheduled",
            "warm": "Warm",
            "committed": "Committed",
            "cold": "Cold",
        }
        for value, label in expected.items():
            with self.subTest(stage=value):
                self.assertEqual(Contact(name="x", stage=value).get_stage_display(), label)


class StagesMatchAdr001Tests(TestCase):
    """Pins the pipeline to the six stages decided in US-2 / ADR-001, in order.

    The code once drifted from the ADR unnoticed; changing a stage must now be a
    deliberate edit to this test, the ADR and a migration together.
    """

    def test_pipeline_is_exactly_the_adr_001_stages_in_order(self):
        self.assertEqual(
            Contact.Stage.choices,
            [
                ("new_lead", "New Lead"),
                ("contacted", "Contacted"),
                ("meeting_scheduled", "Meeting Scheduled"),
                ("warm", "Warm"),
                ("committed", "Committed"),
                ("cold", "Cold"),
            ],
        )


class ContactOrderingTests(TestCase):
    """The list page relies on the default ordering: most recently added first."""

    def _contact_added(self, name, minutes_ago):
        contact = Contact.objects.create(name=name)
        # Pin created_at explicitly so the test never depends on clock resolution.
        Contact.objects.filter(pk=contact.pk).update(created_at=timezone.now() - timedelta(minutes=minutes_ago))
        return contact

    def test_contacts_come_back_newest_first(self):
        self._contact_added("Oldest", minutes_ago=30)
        self._contact_added("Newest", minutes_ago=1)
        self._contact_added("Middle", minutes_ago=10)

        names = list(Contact.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Newest", "Middle", "Oldest"])
