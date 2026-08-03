"""Promote participation formats from JSON enum codes to a child entity table."""

from __future__ import annotations

import json

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import apps.competitions.infrastructure.models.base

_FORMAT_NAMES = {
    "OFFLINE": "Очно",
    "ONLINE": "Онлайн",
}


def _forwards(apps, schema_editor):
    from apps.competitions.domain.value_objects import ParticipationFormatId

    Competition = apps.get_model("competitions", "CompetitionModel")
    ParticipationFormat = apps.get_model("competitions", "ParticipationFormatModel")
    AdmissionRule = apps.get_model("competitions", "AdmissionRuleModel")
    PricingRule = apps.get_model("competitions", "PricingRuleModel")
    now = django.utils.timezone.now()

    for competition in Competition.objects.all():
        raw = competition.enabled_formats or []
        if isinstance(raw, str):
            raw = json.loads(raw)
        codes = list(raw) if isinstance(raw, list) else []
        code_to_id: dict[str, object] = {}
        for index, code in enumerate(codes):
            format_id = ParticipationFormatId.generate().value
            ParticipationFormat.objects.create(
                id=format_id,
                competition_id=competition.id,
                name=_FORMAT_NAMES.get(str(code), str(code)),
                description=None,
                enabled=True,
                sort_order=index,
                created_at=now,
                updated_at=now,
                version=1,
            )
            code_to_id[str(code)] = format_id

        def _ensure(code: str) -> object:
            mapped = code_to_id.get(code)
            if mapped is not None:
                return mapped
            mapped = ParticipationFormatId.generate().value
            ParticipationFormat.objects.create(
                id=mapped,
                competition_id=competition.id,
                name=_FORMAT_NAMES.get(code, code),
                description=None,
                enabled=True,
                sort_order=len(code_to_id),
                created_at=now,
                updated_at=now,
                version=1,
            )
            code_to_id[code] = mapped
            return mapped

        for rule in AdmissionRule.objects.filter(competition_id=competition.id):
            rule.participation_format_id = _ensure(rule.participation_format)
            rule.save(update_fields=["participation_format_id"])

        for rule in PricingRule.objects.filter(competition_id=competition.id):
            rule.participation_format_id = _ensure(rule.participation_format)
            rule.save(update_fields=["participation_format_id"])


def _backwards(apps, schema_editor):
    Competition = apps.get_model("competitions", "CompetitionModel")
    ParticipationFormat = apps.get_model("competitions", "ParticipationFormatModel")
    AdmissionRule = apps.get_model("competitions", "AdmissionRuleModel")
    PricingRule = apps.get_model("competitions", "PricingRuleModel")

    name_to_code = {v: k for k, v in _FORMAT_NAMES.items()}

    for competition in Competition.objects.all():
        formats = list(ParticipationFormat.objects.filter(competition_id=competition.id).order_by("sort_order", "id"))
        id_to_code: dict[object, str] = {}
        codes: list[str] = []
        for fmt in formats:
            code = name_to_code.get(fmt.name, "OFFLINE")
            id_to_code[fmt.id] = code
            if code not in codes:
                codes.append(code)
        competition.enabled_formats = codes
        competition.save(update_fields=["enabled_formats"])

        for rule in AdmissionRule.objects.filter(competition_id=competition.id):
            rule.participation_format = id_to_code.get(rule.participation_format_id, "OFFLINE")
            rule.save(update_fields=["participation_format"])

        for rule in PricingRule.objects.filter(competition_id=competition.id):
            rule.participation_format = id_to_code.get(rule.participation_format_id, "OFFLINE")
            rule.save(update_fields=["participation_format"])


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0005_participant_group_description_sort"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParticipationFormatModel",
            fields=[
                ("id", models.UUIDField(default=apps.competitions.infrastructure.models.base.uuid7, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("deleted_at", models.DateTimeField(blank=True, default=None, editable=False, null=True)),
                ("version", models.PositiveIntegerField(default=1, editable=False)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True, default=None, null=True)),
                ("enabled", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participation_formats",
                        to="competitions.competitionmodel",
                    ),
                ),
            ],
            options={
                "verbose_name": "participation format",
                "verbose_name_plural": "participation formats",
                "db_table": "competitions_participation_format",
                "indexes": [
                    models.Index(fields=["created_at"], name="competition_created_8db9b0_idx"),
                    models.Index(fields=["updated_at"], name="competition_updated_139038_idx"),
                    models.Index(fields=["deleted_at"], name="competition_deleted_2104a4_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="participationformatmodel",
            constraint=models.CheckConstraint(condition=models.Q(("version__gte", 1)), name="competitions_participationformatmodel_version_positive"),
        ),
        migrations.AddConstraint(
            model_name="participationformatmodel",
            constraint=models.UniqueConstraint(fields=("competition", "name"), name="competitions_unique_participation_format_name"),
        ),
        migrations.AddField(
            model_name="admissionrulemodel",
            name="participation_format_id",
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name="pricingrulemodel",
            name="participation_format_id",
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(_forwards, _backwards),
        migrations.AlterField(
            model_name="admissionrulemodel",
            name="participation_format_id",
            field=models.UUIDField(),
        ),
        migrations.AlterField(
            model_name="pricingrulemodel",
            name="participation_format_id",
            field=models.UUIDField(),
        ),
        migrations.RemoveConstraint(
            model_name="admissionrulemodel",
            name="competitions_unique_admission_combination",
        ),
        migrations.RemoveConstraint(
            model_name="pricingrulemodel",
            name="competitions_unique_pricing_combination",
        ),
        migrations.RemoveField(
            model_name="admissionrulemodel",
            name="participation_format",
        ),
        migrations.RemoveField(
            model_name="pricingrulemodel",
            name="participation_format",
        ),
        migrations.RemoveField(
            model_name="competitionmodel",
            name="enabled_formats",
        ),
        migrations.AddConstraint(
            model_name="admissionrulemodel",
            constraint=models.UniqueConstraint(
                fields=(
                    "competition",
                    "category_id",
                    "discipline_id",
                    "age_category_id",
                    "participant_group_id",
                    "participation_format_id",
                ),
                name="competitions_unique_admission_combination",
            ),
        ),
        migrations.AddConstraint(
            model_name="pricingrulemodel",
            constraint=models.UniqueConstraint(
                fields=(
                    "competition",
                    "category_id",
                    "discipline_id",
                    "age_category_id",
                    "participant_group_id",
                    "participation_format_id",
                ),
                name="competitions_unique_pricing_combination",
            ),
        ),
    ]
