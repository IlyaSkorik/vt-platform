"""Scope AgeCategory to a nomination (category) and add type/mixed_calculation_method fields."""

from django.db import migrations, models


def assign_category_to_age_categories(apps, schema_editor):
    """Assign orphan age categories to the first category of their competition."""
    AgeCategoryModel = apps.get_model("competitions", "AgeCategoryModel")
    CategoryModel = apps.get_model("competitions", "CategoryModel")

    for age_cat in AgeCategoryModel.objects.filter(category_id__isnull=True):
        first_category = (
            CategoryModel.objects.filter(competition_id=age_cat.competition_id).order_by("sort_order", "id").first()
        )
        if first_category is not None:
            age_cat.category_id = first_category.id
            age_cat.save(update_fields=["category_id"])
        else:
            age_cat.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0003_age_category_name_sort"),
    ]

    operations = [
        # 1. Add category_id as nullable
        migrations.AddField(
            model_name="agecategorymodel",
            name="category_id",
            field=models.UUIDField(null=True),
        ),
        # 2. Data migration: assign category_id
        migrations.RunPython(assign_category_to_age_categories, migrations.RunPython.noop),
        # 3. Make category_id non-null
        migrations.AlterField(
            model_name="agecategorymodel",
            name="category_id",
            field=models.UUIDField(),
        ),
        # 4. Add type and mixed_calculation_method
        migrations.AddField(
            model_name="agecategorymodel",
            name="type",
            field=models.CharField(max_length=16, default="STANDARD"),
        ),
        migrations.AddField(
            model_name="agecategorymodel",
            name="mixed_calculation_method",
            field=models.CharField(max_length=16, null=True, blank=True, default=None),
        ),
        # 5. Drop old unique constraint (competition, name)
        migrations.RemoveConstraint(
            model_name="agecategorymodel",
            name="competitions_unique_age_category_name",
        ),
        # 6. Add new unique constraint (competition, category_id, name)
        migrations.AddConstraint(
            model_name="agecategorymodel",
            constraint=models.UniqueConstraint(
                fields=["competition", "category_id", "name"],
                name="competitions_unique_age_category_name",
            ),
        ),
        # 7. Add index on category_id
        migrations.AddIndex(
            model_name="agecategorymodel",
            index=models.Index(fields=["category_id"], name="competitions_ag_categor_36fb6f_idx"),
        ),
    ]
