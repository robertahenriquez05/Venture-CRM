"""Shared test helpers. Every page needs a login now (US-8), so client tests start signed in."""

from django.contrib.auth import get_user_model
from django.test import TestCase

TEST_USERNAME = "tester"
TEST_PASSWORD = "test-only-password-123"


def make_test_user():
    return get_user_model().objects.create_user(username=TEST_USERNAME, password=TEST_PASSWORD)


class SignedInTestCase(TestCase):
    """A TestCase whose self.client is already signed in as a normal user."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = make_test_user()

    def _pre_setup(self):
        # Runs before each test's own setUp(), so subclasses don't need to call super().setUp().
        super()._pre_setup()
        self.client.force_login(self.user)
