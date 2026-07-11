# Public-landing configuration JSON bag on the competition root.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0010_contacts_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="competitionmodel",
            name="landing_config",
            field=models.JSONField(default=dict),
        ),
    ]
