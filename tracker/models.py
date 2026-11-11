from django.db import models


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
