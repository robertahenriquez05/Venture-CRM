from django.urls import reverse

from .models import Contact
from .testing import SignedInTestCase


class WalkingSkeletonTests(SignedInTestCase):
    """End-to-end through the real stack: HTTP request -> view -> form -> ORM -> database -> rendered page."""

    def test_list_page_loads_empty(self):
        response = self.client.get(reverse("contact_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No contacts yet")

    def test_add_contact_persists_and_appears_in_list(self):
        response = self.client.post(
            reverse("contact_list"),
            {"name": "Jane Demo", "email": "jane@example.com", "company": "Demo Labs", "stage": "contacted"},
            follow=True,
        )
        # Row really exists in the database
        self.assertEqual(Contact.objects.count(), 1)
        saved = Contact.objects.get()
        self.assertEqual(saved.name, "Jane Demo")
        self.assertEqual(saved.stage, Contact.Stage.CONTACTED)
        # ...and is read back from the database onto the page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jane Demo")
        self.assertContains(response, "Contacted")

    def test_invalid_contact_is_rejected(self):
        response = self.client.post(reverse("contact_list"), {"name": "", "email": "not-an-email", "stage": "new_lead"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), 0)
