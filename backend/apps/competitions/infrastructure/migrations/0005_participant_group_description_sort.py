"""Add description and sort_order to ParticipantGroupModel."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0004_age_category_nomination_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="participantgroupmodel",
            name="description",
            field=models.TextField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="participantgroupmodel",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
