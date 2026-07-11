# Generated manually for PricingCalculationType on pricing rules.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0007_participation_format_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="pricingrulemodel",
            name="calculation_type",
            field=models.CharField(
                choices=[("PER_PARTICIPANT", "PER_PARTICIPANT"), ("PER_PERFORMANCE", "PER_PERFORMANCE")],
                default="PER_PARTICIPANT",
                max_length=32,
            ),
        ),
        migrations.AddConstraint(
            model_name="pricingrulemodel",
            constraint=models.CheckConstraint(
                condition=models.Q(calculation_type__in=["PER_PARTICIPANT", "PER_PERFORMANCE"]),
                name="competitions_pricing_calculation_type_valid",
            ),
        ),
    ]
