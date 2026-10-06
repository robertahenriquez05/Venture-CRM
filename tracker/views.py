from django.shortcuts import redirect, render

from .forms import ContactForm
from .models import Contact


def contact_list(request):
    """Walking skeleton: browser -> URL router -> view -> form -> ORM -> SQLite -> template -> browser."""
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("contact_list")
    else:
        form = ContactForm()

    contacts = Contact.objects.all()
    return render(request, "tracker/contact_list.html", {"form": form, "contacts": contacts})
