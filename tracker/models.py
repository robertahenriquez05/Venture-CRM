from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone


class Tag(models.Model):
    """US-6: a category such as Investor or Mentor. A contact can have several (M3: CONTACT_TAG join table)."""

    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=40, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Contact(models.Model):
    """A founder-relationship contact.

    The CURRENT stage is a fixed choices field on the row (ADR-001), so lists and the board never join.
    Every change to it is also appended to StageChange (ADR-002), which only the detail page reads.
    """

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
    tags = models.ManyToManyField(Tag, blank=True, related_name="contacts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Save, and record a StageChange whenever the stage is set or changes (ADR-002).

        Every write path (the add form, the edit form, the pipeline board, the admin) goes through
        save(), so this is the one place history is written. QuerySet.update() bypasses it on purpose:
        nothing in the app changes stages that way.
        """
        with transaction.atomic():
            if self.pk is None:
                previous = None
            else:
                previous = Contact.objects.filter(pk=self.pk).values_list("stage", flat=True).first()
            super().save(*args, **kwargs)
            if previous != self.stage:
                StageChange.objects.create(contact=self, from_stage=previous or "", to_stage=self.stage)

    @property
    def current_stage_since(self):
        """When the contact entered its current stage (None if no history was recorded)."""
        latest = self.stage_changes.filter(to_stage=self.stage).first()
        return latest.changed_at if latest else None

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


class StageChange(models.Model):
    """ADR-002: append-only history of pipeline-stage changes. Never edited, only added to."""

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="stage_changes")
    from_stage = models.CharField(max_length=20, choices=Contact.Stage.choices, blank=True)  # blank = first stage
    to_stage = models.CharField(max_length=20, choices=Contact.Stage.choices)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at", "-pk"]

    def __str__(self):
        start = self.get_from_stage_display() or "(new)"
        return f"{self.contact}: {start} -> {self.get_to_stage_display()}"
