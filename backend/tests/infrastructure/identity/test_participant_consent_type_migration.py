"""The data step of ``identity.0004_participant_consent_type``.

Splitting the type is a schema change with one piece of judgement in it: rows already
written under the shared ``third_party_data_processing`` have to be sorted into the two
subjects it used to conflate. The sorting rule is that a consent the registry points at
was given about a participant — everything else is left where it is.

Applying the migration is covered by the test database being built from migrations at
all. What is covered here is that rule, because it is the part that can be wrong while
the migration still succeeds.
"""

from __future__ import annotations

import importlib
import uuid

import pytest
from django.apps import apps as django_apps

from apps.identity.infrastructure.models import UserConsentModel
from apps.identity.infrastructure.models.user import UserModel
from apps.participants.infrastructure.models import ParticipantRegistryModel
from apps.teachers.infrastructure.models import TeacherModel

pytestmark = pytest.mark.django_db

_migration = importlib.import_module("apps.identity.infrastructure.migrations.0004_participant_consent_type")

_OLD = "third_party_data_processing"
_NEW = "participant_data_processing"


@pytest.fixture
def account() -> UserModel:
    return UserModel.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        first_name="Olga",
        last_name="Petrova",
        locale="ru",
        timezone="UTC",
        password_algorithm="argon2",
        password_hash="x",
    )


def _consent(account: UserModel, consent_type: str = _OLD) -> UserConsentModel:
    return UserConsentModel.objects.create(
        user=account,
        consent_type=consent_type,
        consent_version="1.0",
        status="active",
    )


def _registry_row(account: UserModel, consent: UserConsentModel) -> ParticipantRegistryModel:
    return ParticipantRegistryModel.objects.create(
        owner_id=account.id,
        first_name="Anna",
        last_name="Sidorova",
        birth_date="1994-06-20",
        gender="female",
        consent_id=consent.id,
        consent_version="1.0",
    )


class TestRetypingTheConsentsAParticipantRestsOn:
    def test_retypes_a_consent_the_registry_points_at(self, account: UserModel) -> None:
        consent = _consent(account)
        _registry_row(account, consent)

        _migration._retype_participant_consents(django_apps, None)

        consent.refresh_from_db()
        assert consent.consent_type == _NEW

    def test_leaves_a_teachers_consent_alone(self, account: UserModel) -> None:
        # The row a teacher points at is the case the shared type was always right for.
        consent = _consent(account)
        TeacherModel.objects.create(
            owner_id=account.id,
            first_name="Marina",
            last_name="Volkova",
            role="Фортепиано",
            status="ACTIVE",
            consent_id=consent.id,
            consent_version="1.0",
        )

        _migration._retype_participant_consents(django_apps, None)

        consent.refresh_from_db()
        assert consent.consent_type == _OLD

    def test_leaves_an_unreferenced_consent_alone(self, account: UserModel) -> None:
        # Nothing points at it, so nothing is known about whom it was given about, and a
        # guess would be worse than the ambiguity it replaced.
        consent = _consent(account)

        _migration._retype_participant_consents(django_apps, None)

        consent.refresh_from_db()
        assert consent.consent_type == _OLD

    def test_does_not_touch_the_other_types(self, account: UserModel) -> None:
        minor = _consent(account, "minor_data_processing")
        _registry_row(account, minor)

        _migration._retype_participant_consents(django_apps, None)

        minor.refresh_from_db()
        assert minor.consent_type == "minor_data_processing"

    def test_reverse_folds_the_type_back(self, account: UserModel) -> None:
        consent = _consent(account, _NEW)

        _migration._untype_participant_consents(django_apps, None)

        consent.refresh_from_db()
        assert consent.consent_type == _OLD
