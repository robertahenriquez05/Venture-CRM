"""Tests for the contact detail page (US-2 edit, US-4 follow-up), interaction log (US-3),
follow-ups panel (US-5) and search (US-7)."""

from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Contact, Interaction
from .test_logging import captured_log
from .views import follow_ups_due


def detail_url(contact):
    return reverse("contact_detail", args=[contact.pk])


class ContactDetailTests(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Jane Demo", email="jane@example.com", company="Demo Labs")

    def test_detail_page_shows_the_contact_and_an_empty_timeline(self):
        response = self.client.get(detail_url(self.contact))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jane Demo")
        self.assertContains(response, "No interactions yet")

    def test_unknown_contact_is_404(self):
        self.assertEqual(self.client.get(reverse("contact_detail", args=[999])).status_code, 404)

    def test_list_links_each_name_to_its_detail_page(self):
        self.assertContains(self.client.get(reverse("contact_list")), f'href="{detail_url(self.contact)}"')

    def test_changing_the_stage_saves_and_redirects_back_with_a_message(self):
        data = {"name": "Jane Demo", "email": "jane@example.com", "company": "Demo Labs", "stage": "warm"}
        response = self.client.post(detail_url(self.contact), data, follow=True)
        self.assertRedirects(response, detail_url(self.contact))
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.stage, Contact.Stage.WARM)
        self.assertContains(response, "Changes saved.")

    def test_saving_without_changes_says_so(self):
        data = {"name": "Jane Demo", "email": "jane@example.com", "company": "Demo Labs", "stage": "new_lead"}
        response = self.client.post(detail_url(self.contact), data, follow=True)
        self.assertContains(response, "Nothing changed.")

    def test_setting_and_clearing_a_follow_up_date(self):
        base = {"name": "Jane Demo", "stage": "new_lead"}
        self.client.post(detail_url(self.contact), {**base, "follow_up_date": "2030-05-01"})
        self.contact.refresh_from_db()
        self.assertEqual(str(self.contact.follow_up_date), "2030-05-01")
        self.client.post(detail_url(self.contact), {**base, "follow_up_date": ""})
        self.contact.refresh_from_db()
        self.assertIsNone(self.contact.follow_up_date)

    def test_invalid_edit_is_not_saved_and_shows_errors(self):
        response = self.client.post(detail_url(self.contact), {"name": "", "stage": "warm"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errorlist")
        self.contact.refresh_from_db()
        self.assertEqual((self.contact.name, self.contact.stage), ("Jane Demo", "new_lead"))

    def test_update_is_logged_with_field_names_not_values(self):
        with captured_log() as log:
            self.client.post(detail_url(self.contact), {"name": "Renamed Person", "stage": "cold"})
            self.client.post(detail_url(self.contact), {"name": "", "stage": "cold"})
        updated = next(line for line in log["lines"] if line["event"] == "contact.updated")
        self.assertEqual(updated["changed_fields"], ["company", "email", "name", "stage"])
        self.assertEqual(updated["stage"], "cold")
        rejected = next(line for line in log["lines"] if line["event"] == "contact.update.rejected")
        self.assertEqual(rejected["invalid_fields"], ["name"])
        self.assertNotIn("Renamed Person", log["text"])


class InteractionLogTests(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Jane Demo")
        self.url = reverse("log_interaction", args=[self.contact.pk])

    def test_logging_an_interaction_adds_it_to_the_timeline(self):
        response = self.client.post(self.url, {"kind": "call", "note": "Talked pricing."}, follow=True)
        self.assertRedirects(response, detail_url(self.contact))
        self.assertContains(response, "Talked pricing.")
        self.assertContains(response, "Call logged.")
        self.assertEqual(self.contact.interactions.get().kind, Interaction.Kind.CALL)

    def test_timeline_is_newest_first(self):
        old = Interaction.objects.create(contact=self.contact, kind="email", note="first")
        Interaction.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=2))
        Interaction.objects.create(contact=self.contact, kind="meeting", note="second")
        notes = [i.note for i in self.client.get(detail_url(self.contact)).context["interactions"]]
        self.assertEqual(notes, ["second", "first"])

    def test_note_is_required(self):
        response = self.client.post(self.url, {"kind": "call", "note": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errorlist")
        self.assertFalse(Interaction.objects.exists())

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_unknown_contact_is_404(self):
        response = self.client.post(reverse("log_interaction", args=[999]), {"kind": "call", "note": "x"})
        self.assertEqual(response.status_code, 404)

    def test_interaction_is_logged_without_the_note_text(self):
        with captured_log() as log:
            self.client.post(self.url, {"kind": "meeting", "note": "Confidential terms discussed"})
            self.client.post(self.url, {"kind": "meeting", "note": ""})
        logged = next(line for line in log["lines"] if line["event"] == "interaction.logged")
        self.assertEqual((logged["contact_id"], logged["kind"]), (self.contact.pk, "meeting"))
        rejected = next(line for line in log["lines"] if line["event"] == "interaction.rejected")
        self.assertEqual(rejected["invalid_fields"], ["note"])
        self.assertNotIn("Confidential", log["text"])

    def test_deleting_a_contact_deletes_its_interactions(self):
        Interaction.objects.create(contact=self.contact, kind="call", note="x")
        self.contact.delete()
        self.assertFalse(Interaction.objects.exists())

    def test_interaction_str(self):
        self.assertEqual(str(Interaction(contact=self.contact, kind="email", note="x")), "Email with Jane Demo")


class FollowUpTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def make(self, name, days):
        date = None if days is None else self.today + timedelta(days=days)
        return Contact.objects.create(name=name, follow_up_date=date)

    def test_status_is_overdue_today_upcoming_or_none(self):
        cases = {-1: "overdue", 0: "today", 3: "upcoming", None: None}
        for days, status in cases.items():
            with self.subTest(days=days):
                self.assertEqual(self.make(f"c{days}", days).follow_up_status, status)

    def test_panel_lists_soonest_first_and_skips_contacts_without_a_date(self):
        later, overdue, none, today = self.make("Later", 5), self.make("Overdue", -2), self.make("None", None), self.make("Today", 0)
        self.assertEqual(follow_ups_due(Contact.objects.all()), [overdue, today, later])

    def test_panel_is_capped(self):
        for i in range(8):
            self.make(f"c{i}", i)
        self.assertEqual(len(follow_ups_due(Contact.objects.all())), 6)

    def test_list_page_shows_due_follow_ups(self):
        self.make("Overdue Person", -1)
        response = self.client.get(reverse("contact_list"))
        self.assertContains(response, "Overdue Person")
        self.assertContains(response, "due-overdue")

    def test_list_page_without_follow_ups_says_so(self):
        self.assertContains(self.client.get(reverse("contact_list")), "No follow-ups scheduled")

    @mock.patch("django.utils.timezone.localdate")
    def test_detail_page_flags_an_overdue_follow_up(self, localdate):
        localdate.return_value = self.today
        contact = self.make("Late Person", -4)
        self.assertContains(self.client.get(detail_url(contact)), "Follow up overdue")


class SearchTests(TestCase):
    def setUp(self):
        Contact.objects.create(name="Maya Chen", company="Northline Ventures", email="maya@example.com")
        Contact.objects.create(name="Tom Nguyen", company="Tech Transfer", email="tom@uni.example")

    def search(self, q):
        return self.client.get(reverse("contact_list"), {"q": q})

    def test_matches_name_company_or_email_case_insensitively(self):
        for q in ("maya", "NORTHLINE", "maya@"):
            with self.subTest(q=q):
                names = [c.name for c in self.search(q).context["contacts"]]
                self.assertEqual(names, ["Maya Chen"])

    def test_summary_and_total_still_describe_everyone(self):
        response = self.search("maya")
        self.assertEqual(response.context["total_count"], 2)
        self.assertContains(response, "2 saved in database")
        self.assertContains(response, "1 found")

    def test_no_match_message(self):
        self.assertContains(self.search("zzz"), "No contacts match")

    def test_blank_query_shows_everyone(self):
        self.assertEqual(len(self.search("   ").context["contacts"]), 2)

    def test_search_logs_that_it_searched_not_what(self):
        with captured_log() as log:
            self.search("Maya Chen")
        loaded = next(line for line in log["lines"] if line["event"] == "contact.list.loaded")
        self.assertEqual((loaded["searched"], loaded["contact_count"]), (True, 1))
        self.assertNotIn("Maya", log["text"])
