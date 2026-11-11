# Brings Contact.stage in line with US-2 / ADR-001 (six stages).
# The schema change (new choices + default) comes with a data migration, because rows
# store the stage KEY: every existing row holding an old key must be rewritten, or it
# fails validation the next time it is edited. This is the cost ADR-001 predicted.

from django.db import migrations, models

OLD_TO_NEW = {
    "lead": "new_lead",
    "contacted": "contacted",
    "meeting": "meeting_scheduled",
    "active": "warm",
    "dormant": "cold",
}
# Reverse is lossy: "committed" had no old equivalent, so it goes back to "active".
NEW_TO_OLD = {
    "new_lead": "lead",
    "contacted": "contacted",
    "meeting_scheduled": "meeting",
    "warm": "active",
    "committed": "active",
    "cold": "dormant",
}


def _remap(mapping):
    def run(apps, schema_editor):
        Contact = apps.get_model("tracker", "Contact")
        for old, new in mapping.items():
            if old != new:
                Contact.objects.filter(stage=old).update(stage=new)

    return run


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contact",
            name="stage",
            field=models.CharField(
                choices=[
                    ("new_lead", "New Lead"),
                    ("contacted", "Contacted"),
                    ("meeting_scheduled", "Meeting Scheduled"),
                    ("warm", "Warm"),
                    ("committed", "Committed"),
                    ("cold", "Cold"),
                ],
                default="new_lead",
                max_length=20,
            ),
        ),
        migrations.RunPython(_remap(OLD_TO_NEW), _remap(NEW_TO_OLD)),
    ]
