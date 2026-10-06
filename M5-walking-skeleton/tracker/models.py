from django.db import models


class Contact(models.Model):
    """A founder-relationship contact. Pipeline stage is a fixed choices field (see ADR-001)."""

    class Stage(models.TextChoices):
        LEAD = "lead", "Lead"
        CONTACTED = "contacted", "Contacted"
        MEETING = "meeting", "Meeting scheduled"
        ACTIVE = "active", "Active relationship"
        DORMANT = "dormant", "Dormant"

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    company = models.CharField(max_length=120, blank=True)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.LEAD)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
