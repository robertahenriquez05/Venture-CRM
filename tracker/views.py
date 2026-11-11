import logging
import time
from collections import Counter

from django.db import DatabaseError
from django.http import HttpResponseServerError
from django.shortcuts import redirect, render
from django.utils.html import escape

from .forms import ContactForm
from .models import Contact
from .observability import current_request_id, log_event

CONTACT_PAGE_TEMPLATE = "tracker/contact_list.html"

log = logging.getLogger("tracker.contacts")


def contact_list(request):
    """Entry point for "/". Only decides which job the request is asking for.

    POST means "add a contact"; any other request means "show the page".
    """
    if request.method == "POST":
        return add_contact(request)
    return show_contact_page(request, ContactForm())


def add_contact(request):
    """Validate and save one contact.

    Valid: save it and redirect back to the list (Post/Redirect/Get).
    Invalid: re-show the page with the user's input and the form's errors.
    """
    form = ContactForm(request.POST)
    if not form.is_valid():
        # Field names only, never the submitted values (they are contact data).
        log_event(log, logging.INFO, "contact.create.rejected", invalid_fields=sorted(form.errors))
        return show_contact_page(request, form)
    started = time.perf_counter()
    try:
        contact = form.save()
    except DatabaseError as exc:
        log_event(
            log,
            logging.ERROR,
            "contact.create.failed",
            error_type=type(exc).__name__,
            error=str(exc),
            db_ms=_ms_since(started),
        )
        raise  # Django turns this into a 500 and logs the stack trace (django.request).
    log_event(
        log, logging.INFO, "contact.created", contact_id=contact.pk, stage=contact.stage, db_ms=_ms_since(started)
    )
    return redirect("contact_list")


def show_contact_page(request, form):
    """Render the contact list page around whichever form it is given (blank or with errors)."""
    started = time.perf_counter()
    contacts = list(contacts_for_list())
    log_event(log, logging.INFO, "contact.list.loaded", contact_count=len(contacts), db_ms=_ms_since(started))
    return render(
        request,
        CONTACT_PAGE_TEMPLATE,
        {"form": form, "contacts": contacts, "stage_summary": stage_summary(contacts)},
    )


def stage_summary(contacts):
    """(value, label, count) for every pipeline stage, in pipeline order. Counted in Python: no extra query."""
    counts = Counter(contact.stage for contact in contacts)
    return [(value, label, counts.get(value, 0)) for value, label in Contact.Stage.choices]


def contacts_for_list():
    """The single place that decides which contacts the list page shows.

    Order comes from Contact.Meta.ordering (newest first, pinned by the M6 ordering tests).
    Future search (US-7) and category filters (US-6) belong here, not in the request handling.
    """
    return Contact.objects.all()


def server_error(request):
    """The 500 page users see when DEBUG is off. Shows the request_id so a report can be traced."""
    reference = getattr(request, "request_id", None) or current_request_id() or "unavailable"
    return HttpResponseServerError(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Venture CRM - Error</title></head>"
        "<body style=\"font-family: system-ui, sans-serif; max-width: 760px; margin: 40px auto; padding: 0 16px;\">"
        "<h1>Something went wrong</h1>"
        "<p>Venture CRM could not finish that request. If you were adding a contact, it was not saved.</p>"
        f"<p>Reference code: <code>{escape(reference)}</code></p>"
        "</body></html>"
    )


def _ms_since(started):
    return round((time.perf_counter() - started) * 1000, 1)
