"""Tests for the pipeline board, stage history (ADR-002), tags (US-6), delete, and sign-in (US-8)."""

import os
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Contact, Interaction, StageChange, Tag
from .test_logging import captured_log
from .testing import TEST_PASSWORD, TEST_USERNAME, SignedInTestCase


def detail_url(contact):
    return reverse("contact_detail", args=[contact.pk])


class StageHistoryTests(SignedInTestCase):
    def test_new_contact_records_its_first_stage(self):
        contact = Contact.objects.create(name="Jane Demo", stage="contacted")
        change = contact.stage_changes.get()
        self.assertEqual((change.from_stage, change.to_stage), ("", "contacted"))

    def test_each_stage_change_appends_one_row(self):
        contact = Contact.objects.create(name="Jane Demo")
        for stage in ("contacted", "warm", "committed"):
            contact.stage = stage
            contact.save()
        path = [(c.from_stage, c.to_stage) for c in contact.stage_changes.order_by("pk")]
        self.assertEqual(path, [("", "new_lead"), ("new_lead", "contacted"), ("contacted", "warm"), ("warm", "committed")])

    def test_saving_without_a_stage_change_adds_nothing(self):
        contact = Contact.objects.create(name="Jane Demo")
        contact.company = "New Co"
        contact.save()
        self.assertEqual(contact.stage_changes.count(), 1)

    def test_edit_form_records_history(self):
        contact = Contact.objects.create(name="Jane Demo")
        self.client.post(detail_url(contact), {"name": "Jane Demo", "stage": "warm"})
        self.assertEqual(contact.stage_changes.first().to_stage, "warm")

    def test_detail_page_shows_history_and_time_in_stage(self):
        contact = Contact.objects.create(name="Jane Demo")
        response = self.client.get(detail_url(contact))
        self.assertContains(response, "Stage history")
        self.assertContains(response, "In <b>New Lead</b> for")

    def test_contact_without_history_says_it_predates_history(self):
        contact = Contact.objects.create(name="Old Contact")
        contact.stage_changes.all().delete()
        self.assertIsNone(contact.current_stage_since)
        self.assertContains(self.client.get(detail_url(contact)), "since before stage history was recorded")

    def test_str(self):
        contact = Contact.objects.create(name="Jane Demo")
        first = contact.stage_changes.get()
        self.assertEqual(str(first), "Jane Demo: (new) -> New Lead")
        contact.stage = "cold"
        contact.save()
        self.assertEqual(str(contact.stage_changes.first()), "Jane Demo: New Lead -> Cold")


class PipelineBoardTests(SignedInTestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Jane Demo", stage="contacted")
        self.move_url = reverse("move_stage", args=[self.contact.pk])

    def test_board_has_one_column_per_stage_in_order(self):
        response = self.client.get(reverse("pipeline"))
        self.assertEqual([col["value"] for col in response.context["columns"]], Contact.Stage.values)
        contacted = response.context["columns"][1]
        self.assertEqual([c.name for c in contacted["contacts"]], ["Jane Demo"])

    def test_drag_and_drop_move_returns_json_and_records_history(self):
        with captured_log() as log:
            response = self.client.post(self.move_url, {"stage": "warm"}, headers={"Accept": "application/json"})
        self.assertEqual(response.json(), {"id": self.contact.pk, "stage": "warm", "label": "Warm"})
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.stage, "warm")
        self.assertEqual(self.contact.stage_changes.first().from_stage, "contacted")
        moved = next(line for line in log["lines"] if line["event"] == "contact.stage.changed")
        self.assertEqual((moved["from_stage"], moved["to_stage"]), ("contacted", "warm"))

    def test_form_move_without_javascript_redirects_to_the_board(self):
        response = self.client.post(self.move_url, {"stage": "committed"}, follow=True)
        self.assertRedirects(response, reverse("pipeline"))
        self.assertContains(response, "Jane Demo moved to Committed.")

    def test_moving_to_the_same_stage_adds_no_history(self):
        self.client.post(self.move_url, {"stage": "contacted"}, headers={"Accept": "application/json"})
        self.assertEqual(self.contact.stage_changes.count(), 1)

    def test_unknown_stage_is_rejected(self):
        response = self.client.post(self.move_url, {"stage": "hot"})
        self.assertEqual(response.status_code, 400)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.stage, "contacted")

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.move_url).status_code, 405)


class TagTests(SignedInTestCase):
    def setUp(self):
        self.investor = Tag.objects.get(slug="investor")
        self.mentor = Tag.objects.get(slug="mentor")
        self.maya = Contact.objects.create(name="Maya Chen")
        self.maya.tags.set([self.investor])
        self.tom = Contact.objects.create(name="Tom Nguyen")
        self.tom.tags.set([self.mentor, self.investor])
        Contact.objects.create(name="No Tags")

    def test_default_categories_exist(self):
        self.assertEqual(
            sorted(Tag.objects.values_list("slug", flat=True)),
            ["advisor", "customer", "investor", "mentor", "partner", "regulatory"],
        )
        self.assertEqual(str(self.investor), "Investor")

    def test_filtering_by_tag(self):
        response = self.client.get(reverse("contact_list"), {"tag": "mentor"})
        self.assertEqual([c.name for c in response.context["contacts"]], ["Tom Nguyen"])
        self.assertContains(response, "Mentors")
        self.assertEqual(response.context["total_count"], 3)

    def test_unknown_tag_shows_everyone(self):
        self.assertEqual(len(self.client.get(reverse("contact_list"), {"tag": "nope"}).context["contacts"]), 3)

    def test_tag_with_no_contacts_says_so(self):
        self.assertContains(self.client.get(reverse("contact_list"), {"tag": "customer"}), "No contacts tagged Customer")

    def test_tags_can_be_set_from_the_edit_form(self):
        self.client.post(detail_url(self.maya), {"name": "Maya Chen", "stage": "new_lead", "tags": [self.mentor.pk]})
        self.assertEqual(list(self.maya.tags.values_list("slug", flat=True)), ["mentor"])

    def test_list_shows_tags(self):
        self.assertContains(self.client.get(reverse("contact_list")), '<span class="tag">Mentor</span>')


class DeleteContactTests(SignedInTestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Jane Demo")
        Interaction.objects.create(contact=self.contact, kind="call", note="x")
        self.url = reverse("delete_contact", args=[self.contact.pk])

    def test_get_asks_for_confirmation_and_deletes_nothing(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Delete Jane Demo?")
        self.assertContains(response, "1 logged interaction ")
        self.assertTrue(Contact.objects.exists())

    def test_post_deletes_contact_interactions_and_history(self):
        with captured_log() as log:
            response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse("contact_list"))
        self.assertContains(response, "Jane Demo was deleted.")
        self.assertFalse(Contact.objects.exists() or Interaction.objects.exists() or StageChange.objects.exists())
        deleted = next(line for line in log["lines"] if line["event"] == "contact.deleted")
        self.assertNotIn("Jane Demo", str(deleted))

    def test_unknown_contact_is_404(self):
        self.assertEqual(self.client.post(reverse("delete_contact", args=[999])).status_code, 404)


class SignInRequiredTests(TestCase):
    """Signed-out visitors see nothing but the login page (and the health check)."""

    def setUp(self):
        self.contact = Contact.objects.create(name="Private Person")

    def test_every_page_redirects_to_login(self):
        pages = [
            reverse("contact_list"),
            reverse("pipeline"),
            detail_url(self.contact),
            reverse("delete_contact", args=[self.contact.pk]),
        ]
        for url in pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith(reverse("login")))

    def test_writes_are_refused_too(self):
        self.client.post(reverse("move_stage", args=[self.contact.pk]), {"stage": "cold"})
        self.client.post(reverse("delete_contact", args=[self.contact.pk]))
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.stage, "new_lead")

    def test_health_check_needs_no_login(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual((response.status_code, response.content), (200, b"ok"))

    def test_login_page_renders(self):
        self.assertContains(self.client.get(reverse("login")), "Welcome back")

    def test_sign_in_and_out_are_logged_without_the_username(self):
        get_user_model().objects.create_user(username=TEST_USERNAME, password=TEST_PASSWORD)
        with captured_log() as log:
            self.client.post(reverse("login"), {"username": TEST_USERNAME, "password": "wrong"})
            self.client.post(reverse("login"), {"username": TEST_USERNAME, "password": TEST_PASSWORD})
            self.client.post(reverse("logout"))
        events = [line["event"] for line in log["lines"] if line["event"].startswith("auth.")]
        self.assertEqual(events, ["auth.login.failed", "auth.login", "auth.logout"])
        self.assertNotIn(TEST_USERNAME, log["text"])

    def test_signed_in_user_sees_their_name_and_a_sign_out_button(self):
        user = get_user_model().objects.create_user(username="roberta", password=TEST_PASSWORD)
        self.client.force_login(user)
        response = self.client.get(reverse("contact_list"))
        self.assertContains(response, "roberta")
        self.assertContains(response, "Sign out")


class EnsureDemoUserCommandTests(TestCase):
    def run_command(self, **env):
        out = StringIO()
        with mock.patch.dict(os.environ, env, clear=False):
            call_command("ensure_demo_user", stdout=out)
        return out.getvalue()

    def test_does_nothing_without_a_password(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            out = StringIO()
            call_command("ensure_demo_user", stdout=out)
        self.assertIn("not set", out.getvalue())
        self.assertFalse(get_user_model().objects.exists())

    def test_creates_then_updates_the_account(self):
        self.assertIn("Created", self.run_command(VENTURE_CRM_DEMO_PASSWORD="first-pass", VENTURE_CRM_DEMO_USERNAME=""))
        user = get_user_model().objects.get(username="demo")
        self.assertTrue(user.check_password("first-pass") and user.is_superuser)
        self.assertIn("Updated", self.run_command(VENTURE_CRM_DEMO_PASSWORD="second-pass"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("second-pass"))


class AdminTests(TestCase):
    def test_admin_contact_page_shows_history_read_only(self):
        admin_user = get_user_model().objects.create_superuser("admin", "admin@example.com", TEST_PASSWORD)
        self.client.force_login(admin_user)
        contact = Contact.objects.create(name="Jane Demo")
        response = self.client.get(reverse("admin:tracker_contact_change", args=[contact.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stage changes")
        self.assertNotContains(response, "Add another Stage change")
