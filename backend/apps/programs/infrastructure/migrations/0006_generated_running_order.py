"""The rules a running order was generated from, kept on the programme (VT-86).

One JSON column, empty for every programme that already exists: nothing was generated
before this migration, so a hand-built programme reads back with no rules - which is
exactly what ``{}`` means.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0005_custom_columns_and_live_progress"),
    ]

    operations = [
        migrations.AddField(
            model_name="programmodel",
            name="arrangement",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
