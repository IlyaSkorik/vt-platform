"""«Отменён» — a state of the day the progress vocabulary did not have.

«Не вышел» and «отменён» are different facts: one the host stepped over and may come
back to, the other is not happening today. Every screen reading the programme needs the
second one, so it joins the enum rather than living as a note — and widening the enum
means rebuilding the check constraint that enumerates it.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0007_undo_rebuild"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="programitemmodel",
            name="programs_item_progress_valid",
        ),
        migrations.AlterField(
            model_name="programitemmodel",
            name="progress",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("ON_STAGE", "On stage"),
                    ("PERFORMED", "Performed"),
                    ("SKIPPED", "Skipped"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="PENDING",
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="programitemmodel",
            constraint=models.CheckConstraint(
                condition=models.Q(("progress__in", ["PENDING", "ON_STAGE", "PERFORMED", "SKIPPED", "CANCELLED"])),
                name="programs_item_progress_valid",
            ),
        ),
    ]
