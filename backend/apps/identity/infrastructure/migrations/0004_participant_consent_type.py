"""Give an adult participant's consent a type of its own.

An adult participant and a teacher are both grown-ups entered by somebody else, so
both rested on ``third_party_data_processing`` — the same statement, that the person
entering them holds their consent. One type for two subjects means the journal cannot
tell them apart, and neither can the check that guards a record: a consent recorded
while adding a teacher passed as the basis for holding a participant, and the other way
round. What each consent authorises is exactly what the type has to say.

Existing rows *can* be told apart, so they are. A consent the registry points at
(``participants_registry.consent_id``) was given about a participant; one a teacher
points at was given about a teacher; anything nothing points at is left alone, because a
guess would be worse than the ambiguity it replaced.

The retype runs while the check constraint is off — between its removal and its
recreation — because the value it writes is one the old constraint forbids.
"""

from __future__ import annotations

from django.db import migrations, models

_OLD = "third_party_data_processing"
_NEW = "participant_data_processing"

_CONSENT_TYPES = [
    "terms_of_service",
    "privacy_policy",
    "data_processing",
    "minor_data_processing",
    _NEW,
    _OLD,
    "marketing",
]


def _retype_participant_consents(apps, schema_editor):
    """Point every consent a registry row leans on at the participant type."""
    UserConsentModel = apps.get_model("identity", "UserConsentModel")
    ParticipantRegistryModel = apps.get_model("participants", "ParticipantRegistryModel")

    referenced = ParticipantRegistryModel.objects.exclude(consent_id=None).values_list("consent_id", flat=True)
    UserConsentModel.objects.filter(id__in=list(referenced), consent_type=_OLD).update(consent_type=_NEW)


def _untype_participant_consents(apps, schema_editor):
    """Fold the participant type back into the shared one."""
    UserConsentModel = apps.get_model("identity", "UserConsentModel")
    UserConsentModel.objects.filter(consent_type=_NEW).update(consent_type=_OLD)


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0003_consent_reference"),
        # The retype reads the registry to tell a participant's consent from a teacher's.
        ("participants", "0005_registry_consent_reference"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="userconsentmodel",
            name="identity_consent_type_valid",
        ),
        migrations.AlterField(
            model_name="userconsentmodel",
            name="consent_type",
            field=models.CharField(
                choices=[
                    ("terms_of_service", "Terms of Service"),
                    ("privacy_policy", "Privacy Policy"),
                    ("data_processing", "Data Processing"),
                    ("minor_data_processing", "Minor Data Processing"),
                    ("participant_data_processing", "Participant Data Processing"),
                    ("third_party_data_processing", "Third-Party Data Processing"),
                    ("marketing", "Marketing"),
                ],
                default="terms_of_service",
                max_length=32,
            ),
        ),
        migrations.RunPython(_retype_participant_consents, _untype_participant_consents),
        migrations.AddConstraint(
            model_name="userconsentmodel",
            constraint=models.CheckConstraint(
                condition=models.Q(("consent_type__in", _CONSENT_TYPES)),
                name="identity_consent_type_valid",
            ),
        ),
    ]
