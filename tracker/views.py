import logging
import time
from collections import Counter

from django.contrib import messages
from django.db import DatabaseError
from django.db.models import Q
from django.http import HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_POST

from .forms import ContactForm, InteractionForm
from .models import Contact
from .observability import current_request_id, log_event

CONTACT_PAGE_TEMPLATE = "tracker/contact_list.html"
CONTACT_DETAIL_TEMPLATE = "tracker/contact_detail.html"
FOLLOW_UP_PANEL_SIZE = 6

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
    query = request.GET.get("q", "").strip()
    contacts = list(contacts_for_list(query))
    # The summary and follow-ups always describe the whole pipeline, not just the search results.
    everyone = list(Contact.objects.all()) if query else contacts
    log_event(
        log,
        logging.INFO,
        "contact.list.loaded",
        contact_count=len(contacts),
        searched=bool(query),  # whether, never what: the query can be a person's name
        db_ms=_ms_since(started),
    )
    return render(
        request,
        CONTACT_PAGE_TEMPLATE,
        {
            "form": form,
            "contacts": contacts,
            "query": query,
            "total_count": len(everyone),
            "stage_summary": stage_summary(everyone),
            "follow_ups": follow_ups_due(everyone),
        },
    )


def stage_summary(contacts):
    """(value, label, count) for every pipeline stage, in pipeline order. Counted in Python: no extra query."""
    counts = Counter(contact.stage for contact in contacts)
    return [(value, label, counts.get(value, 0)) for value, label in Contact.Stage.choices]


def follow_ups_due(contacts, limit=FOLLOW_UP_PANEL_SIZE):
    """US-5: contacts with a follow-up date, soonest (most overdue) first."""
    scheduled = [contact for contact in contacts if contact.follow_up_date]
    scheduled.sort(key=lambda contact: (contact.follow_up_date, contact.name.lower()))
    return scheduled[:limit]


def contacts_for_list(query=""):
    """The single place that decides which contacts the list page shows.

    Order comes from Contact.Meta.ordering (newest first, pinned by the M6 ordering tests).
    US-7 search matches name, company or email, case-insensitively. Category filters (US-6) belong here too.
    """
    contacts = Contact.objects.all()
    if query:
        contacts = contacts.filter(Q(name__icontains=query) | Q(company__icontains=query) | Q(email__icontains=query))
    return contacts


def contact_detail(request, pk):
    """One contact: edit its details and stage (US-2), schedule its follow-up (US-4), see its timeline (US-3)."""
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == "POST":
        return update_contact(request, contact)
    return show_contact_detail(request, contact, ContactForm(instance=contact), InteractionForm())


def update_contact(request, contact):
    form = ContactForm(request.POST, instance=contact)
    if not form.is_valid():
        log_event(
            log, logging.INFO, "contact.update.rejected", contact_id=contact.pk, invalid_fields=sorted(form.errors)
        )
        return show_contact_detail(request, contact, form, InteractionForm())
    changed = sorted(form.changed_data)
    form.save()
    log_event(log, logging.INFO, "contact.updated", contact_id=contact.pk, changed_fields=changed, stage=contact.stage)
    messages.success(request, "Changes saved." if changed else "Nothing changed.")
    return redirect(contact)


@require_POST
def log_interaction(request, pk):
    """US-3: add one call/email/meeting note to a contact's timeline."""
    contact = get_object_or_404(Contact, pk=pk)
    form = InteractionForm(request.POST)
    if not form.is_valid():
        log_event(
            log, logging.INFO, "interaction.rejected", contact_id=contact.pk, invalid_fields=sorted(form.errors)
        )
        return show_contact_detail(request, contact, ContactForm(instance=contact), form)
    interaction = form.save(commit=False)
    interaction.contact = contact
    interaction.save()
    log_event(
        log,
        logging.INFO,
        "interaction.logged",
        contact_id=contact.pk,
        interaction_id=interaction.pk,
        kind=interaction.kind,
    )
    messages.success(request, f"{interaction.get_kind_display()} logged.")
    return redirect(contact)


def show_contact_detail(request, contact, form, interaction_form):
    return render(
        request,
        CONTACT_DETAIL_TEMPLATE,
        {
            "contact": contact,
            "form": form,
            "interaction_form": interaction_form,
            "interactions": list(contact.interactions.all()),
            "today": timezone.localdate(),
        },
    )


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
