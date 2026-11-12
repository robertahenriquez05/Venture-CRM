from django.db import models
from django.urls import reverse
from django.utils import timezone


class Contact(models.Model):
    """A founder-relationship contact. Pipeline stage is a fixed choices field (see ADR-001)."""

    class Stage(models.TextChoices):
        NEW_LEAD = "new_lead", "New Lead"
        CONTACTED = "contacted", "Contacted"
        MEETING_SCHEDULED = "meeting_scheduled", "Meeting Scheduled"
        WARM = "warm", "Warm"
        COMMITTED = "committed", "Committed"
        COLD = "cold", "Cold"

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    company = models.CharField(max_length=120, blank=True)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW_LEAD)
    # US-4: one follow-up date per contact, set and cleared in place (M3: a field, not a FOLLOW_UP table).
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("contact_detail", args=[self.pk])

    @property
    def follow_up_status(self):
        """US-5: "overdue", "today", "upcoming", or None when no follow-up is set."""
        if not self.follow_up_date:
            return None
        today = timezone.localdate()
        if self.follow_up_date < today:
            return "overdue"
        return "today" if self.follow_up_date == today else "upcoming"


class Interaction(models.Model):
    """US-3: one logged call, email or meeting with a contact. The timestamp is set by the app, never edited."""

    class Kind(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="interactions")
    kind = models.CharField("type", max_length=10, choices=Kind.choices, default=Kind.CALL)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.get_kind_display()} with {self.contact}"
