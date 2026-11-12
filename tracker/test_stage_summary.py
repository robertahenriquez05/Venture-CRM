from django.urls import reverse

from .models import Contact
from .testing import SignedInTestCase
from .views import stage_summary


class StageSummaryTests(SignedInTestCase):
    def test_every_stage_is_listed_in_pipeline_order_with_its_count(self):
        contacts = [Contact(name="a", stage="warm"), Contact(name="b", stage="warm"), Contact(name="c", stage="cold")]
        summary = stage_summary(contacts)
        self.assertEqual([value for value, _label, _n in summary], [v for v, _ in Contact.Stage.choices])
        counts = {value: n for value, _label, n in summary}
        self.assertEqual(counts["warm"], 2)
        self.assertEqual(counts["cold"], 1)
        self.assertEqual(counts["new_lead"], 0)

    def test_list_page_shows_the_stage_summary(self):
        Contact.objects.create(name="Jane Demo", stage="committed")
        response = self.client.get(reverse("contact_list"))
        self.assertEqual(response.context["stage_summary"][4], ("committed", "Committed", 1))
