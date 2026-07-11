"""Add name and sort_order to AgeCategoryModel; populate name from age range."""

from django.db import migrations, models


def populate_age_category_names(apps, schema_editor):
    AgeCategoryModel = apps.get_model("competitions", "AgeCategoryModel")
    for row in AgeCategoryModel.objects.all():
        row.name = f"{row.min_age}-{row.max_age}"
        row.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0002_category_discipline_sort_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="agecategorymodel",
            name="name",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="agecategorymodel",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(populate_age_category_names, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="agecategorymodel",
            constraint=models.UniqueConstraint(
                fields=["competition", "name"],
                name="competitions_unique_age_category_name",
            ),
        ),
    ]
