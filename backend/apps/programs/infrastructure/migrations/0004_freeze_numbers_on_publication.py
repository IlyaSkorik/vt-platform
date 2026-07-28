"""Numbers follow the running order until the programme is first published.

Programmes that already have a public edition are treated as frozen from the moment that
edition was created: their numbers have been out in the world since then, so they must not
start following the order again. Programmes with no link yet stay unfrozen, which is the
state they are actually in - still being assembled.
"""

from django.db import migrations, models
from django.db.models import Min


def freeze_already_published(apps, schema_editor):
    """Backfill the freeze instant from each programme's earliest public edition."""
    program_model = apps.get_model("programs", "ProgramModel")
    share_model = apps.get_model("programs", "ProgramShareModel")
    published = share_model.objects.values("program_id").annotate(first=Min("created_at"))
    for row in published:
        program_model.objects.filter(id=row["program_id"]).update(numbers_frozen_at=row["first"])


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0003_permanent_item_numbers"),
    ]

    operations = [
        migrations.AddField(
            model_name="programmodel",
            name="numbers_frozen_at",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        # Reversing needs no counterpart: dropping the column drops the data with it.
        migrations.RunPython(freeze_already_published, migrations.RunPython.noop),
    ]
