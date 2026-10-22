"""The restore point a rebuild leaves behind, so «Пересобрать» can be undone.

Null for every programme that already exists, including those rebuilt before this
migration: their replaced rows are still on disk, but nothing recorded which instant
to look for them at, so those cannot be offered an undo. New rebuilds can.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0006_generated_running_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="programmodel",
            name="rebuilt_at",
            field=models.DateTimeField(blank=True, default=None, editable=False, null=True),
        ),
    ]
