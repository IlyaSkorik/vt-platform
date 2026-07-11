"""Add description and sort_order to CategoryModel, sort_order to DisciplineModel."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="categorymodel",
            name="description",
            field=models.TextField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="categorymodel",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="disciplinemodel",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
