"""Create or update the sign-in account for the deployed site from environment variables.

VENTURE_CRM_DEMO_PASSWORD  required; Render generates it (see render.yaml) and shows it under Environment.
VENTURE_CRM_DEMO_USERNAME  optional, default "demo".

The account is a superuser, so the same sign-in also opens /admin/. With no password set
(local development, CI) the command does nothing.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create/update the demo sign-in account from VENTURE_CRM_DEMO_USERNAME / VENTURE_CRM_DEMO_PASSWORD."

    def handle(self, *args, **options):
        password = os.environ.get("VENTURE_CRM_DEMO_PASSWORD", "")
        if not password:
            self.stdout.write("VENTURE_CRM_DEMO_PASSWORD not set; no account created.")
            return
        username = os.environ.get("VENTURE_CRM_DEMO_USERNAME", "") or "demo"
        user, created = get_user_model().objects.get_or_create(username=username)
        user.is_staff = user.is_superuser = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} sign-in account '{username}'."))
