"""Sign-in events in the same structured log as everything else (user id only, never the username typed)."""

import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .observability import log_event

log = logging.getLogger("tracker.auth")


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    log_event(log, logging.INFO, "auth.login", user_id=user.pk)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    log_event(log, logging.INFO, "auth.logout", user_id=getattr(user, "pk", None))


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    log_event(log, logging.WARNING, "auth.login.failed")
