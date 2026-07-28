"""Give every slot a permanent number, independent of its place in the running order.

Existing rows are backfilled from ``position``: until now the two were the same thing, so
a slot's ordinal *is* the number its participant was told. The programme's issue counter
is seeded from the highest of them, so the next slot added continues the sequence instead
of colliding with a number already in use.
"""

from django.db import migrations, models
from django.db.models import F, Max


def backfill_numbers(apps, schema_editor):
    """Seed item numbers from their ordinals, and each programme's counter from those."""
    item_model = apps.get_model("programs", "ProgramItemModel")
    program_model = apps.get_model("programs", "ProgramModel")
    item_model.objects.filter(number=0).update(number=F("position"))
    for program in program_model.objects.all().iterator():
        highest = item_model.objects.filter(program_id=program.id).aggregate(top=Max("number"))["top"] or 0
        if highest:
            program_model.objects.filter(id=program.id).update(numbers_issued=highest)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0002_programsharemodel_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="programitemmodel",
            name="number",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="programmodel",
            name="numbers_issued",
            field=models.PositiveIntegerField(default=0),
        ),
        # Reversing needs no counterpart: dropping the columns drops the data with them.
        migrations.RunPython(backfill_numbers, migrations.RunPython.noop),
    ]
