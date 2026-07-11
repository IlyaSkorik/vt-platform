# Additional services: billing model, format availability, required, sort order.

from django.db import migrations, models


def backfill_available_formats(apps, schema_editor):
    """Scope existing services to all formats of their competition (legacy → multi-select)."""
    AdditionalServiceModel = apps.get_model("competitions", "AdditionalServiceModel")
    ParticipationFormatModel = apps.get_model("competitions", "ParticipationFormatModel")

    formats_by_competition: dict[object, list[str]] = {}
    for row in ParticipationFormatModel.objects.all().only("id", "competition_id"):
        formats_by_competition.setdefault(row.competition_id, []).append(str(row.id))

    for service in AdditionalServiceModel.objects.all().only("id", "competition_id", "available_format_ids"):
        service.available_format_ids = formats_by_competition.get(service.competition_id, [])
        service.save(update_fields=["available_format_ids"])


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0008_pricing_calculation_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="additionalservicemodel",
            name="billing_model",
            field=models.CharField(
                choices=[("PER_PARTICIPANT", "PER_PARTICIPANT"), ("PER_PERFORMANCE", "PER_PERFORMANCE")],
                default="PER_PARTICIPANT",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="additionalservicemodel",
            name="available_format_ids",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="additionalservicemodel",
            name="required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="additionalservicemodel",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name="additionalservicemodel",
            constraint=models.CheckConstraint(
                condition=models.Q(billing_model__in=["PER_PARTICIPANT", "PER_PERFORMANCE"]),
                name="competitions_service_billing_model_valid",
            ),
        ),
        migrations.AddIndex(
            model_name="additionalservicemodel",
            index=models.Index(fields=["competition", "sort_order"], name="competitions_addsvc_sort_idx"),
        ),
        migrations.RunPython(backfill_available_formats, migrations.RunPython.noop),
    ]
