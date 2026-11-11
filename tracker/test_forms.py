"""
M6 unit tests for ContactForm: the validation rules that decide what is
allowed into the database. Each test states a rule a user would notice
(what gets accepted, rejected, or cleaned up), not how the form is built.
"""

from django.test import TestCase

from .forms import ContactForm
from .models import Contact


def make_form(**overrides):
    data = {"name": "Jane Demo", "email": "jane@example.com", "company": "Demo Labs", "stage": "new_lead"}
    data.update(overrides)
    return ContactForm(data=data)


class ContactFormValidationTests(TestCase):
    def test_complete_contact_is_valid(self):
        self.assertTrue(make_form().is_valid())

    def test_email_and_company_are_optional(self):
        form = make_form(email="", company="")
        self.assertTrue(form.is_valid(), form.errors)

    def test_name_is_required(self):
        form = make_form(name="")
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_whitespace_only_name_is_rejected(self):
        form = make_form(name="    ")
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_name_of_exactly_120_characters_is_accepted(self):
        self.assertTrue(make_form(name="x" * 120).is_valid())

    def test_name_of_121_characters_is_rejected(self):
        form = make_form(name="x" * 121)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_malformed_email_is_rejected(self):
        for bad in ["not-an-email", "jane@", "@example.com", "jane example.com"]:
            with self.subTest(email=bad):
                form = make_form(email=bad)
                self.assertFalse(form.is_valid())
                self.assertIn("email", form.errors)

    def test_every_pipeline_stage_is_accepted(self):
        for value, _label in Contact.Stage.choices:
            with self.subTest(stage=value):
                self.assertTrue(make_form(stage=value).is_valid())

    def test_stage_outside_the_pipeline_is_rejected(self):
        for bad in ["won", "LEAD", ""]:
            with self.subTest(stage=bad):
                form = make_form(stage=bad)
                self.assertFalse(form.is_valid())
                self.assertIn("stage", form.errors)


class ContactFormSaveTests(TestCase):
    def test_saving_a_valid_form_stores_exactly_what_was_entered(self):
        make_form(stage="meeting_scheduled").save()

        saved = Contact.objects.get()
        self.assertEqual(
            (saved.name, saved.email, saved.company, saved.stage),
            ("Jane Demo", "jane@example.com", "Demo Labs", "meeting_scheduled"),
        )

    def test_surrounding_whitespace_is_trimmed_before_saving(self):
        make_form(name="  Jane Demo  ", company="  Demo Labs ").save()

        saved = Contact.objects.get()
        self.assertEqual(saved.name, "Jane Demo")
        self.assertEqual(saved.company, "Demo Labs")
