"""
M6 unit tests for the Contact model: defaults, display, and the order
contacts come back from the database (which is the order the list page shows).
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Contact


class ContactModelTests(TestCase):
    def test_new_contact_starts_in_the_lead_stage(self):
        contact = Contact.objects.create(name="Jane Demo")
        self.assertEqual(contact.stage, "lead")

    def test_creation_time_is_recorded_automatically(self):
        before = timezone.now()
        contact = Contact.objects.create(name="Jane Demo")
        after = timezone.now()
        self.assertTrue(before <= contact.created_at <= after)

    def test_contact_is_shown_by_its_name(self):
        self.assertEqual(str(Contact(name="Jane Demo")), "Jane Demo")

    def test_stage_is_displayed_with_its_human_readable_label(self):
        expected = {
            "lead": "Lead",
            "contacted": "Contacted",
            "meeting": "Meeting scheduled",
            "active": "Active relationship",
            "dormant": "Dormant",
        }
        for value, label in expected.items():
            with self.subTest(stage=value):
                self.assertEqual(Contact(name="x", stage=value).get_stage_display(), label)


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
