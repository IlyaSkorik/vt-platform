# Contacts-module configuration JSON bag on the competition root.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0009_additional_service_formats_billing"),
    ]

    operations = [
        migrations.AddField(
            model_name="competitionmodel",
            name="contacts_config",
            field=models.JSONField(default=dict),
        ),
    ]
