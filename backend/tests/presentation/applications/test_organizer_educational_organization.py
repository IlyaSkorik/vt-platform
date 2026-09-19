"""Учреждение в рабочей карточке организатора.

Карточка называла фестиваль, номера, статус и заказчика — но не учреждение, от
которого заявка пришла. Очередь же разбирают именно школами: одна присылает
десяток номеров, и сверять оплату, звонить и собирать программу удобнее по ней.

Учреждение берётся из реестра участников кабинета, а не из снимка на заявке.
Снимок там есть, но его никто не пишет: ручка выбора учреждения на заявке
существует, а мастер подачи её не вызывает — поэтому карточка, читавшая снимок,
не показывала ничего вообще. Реестр участников организатора ходит в те же строки
и по той же причине.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_django.fixtures import DjangoAssertNumQueries

from apps.applications.application.dto import ParticipantView
from apps.applications.presentation.api.v1.organizer.views import _educational_organizations
from apps.participants.infrastructure.models import (
    EducationalOrganizationModel,
    ParticipantOrganizationMembershipModel,
    ParticipantRegistryModel,
    uuid7,
)

pytestmark = pytest.mark.django_db

_OWNER = uuid7()


def _participant(*, registry_participant_id: str | None) -> ParticipantView:
    return ParticipantView(
        id=str(uuid7()),
        display_name="Петрова Мария",
        first_name="Мария",
        last_name="Петрова",
        middle_name=None,
        birth_date=None,
        gender=None,
        registry_participant_id=registry_participant_id,
        member_count=1,
        members=(),
    )


def _registry_row() -> ParticipantRegistryModel:
    return ParticipantRegistryModel.objects.create(
        owner_id=_OWNER,
        first_name="Мария",
        last_name="Петрова",
        birth_date="2014-05-01",
        gender="FEMALE",
    )


def _organization(name: str) -> EducationalOrganizationModel:
    return EducationalOrganizationModel.objects.create(owner_id=_OWNER, name=name, organization_type="SCHOOL")


def _enrol(participant: ParticipantRegistryModel, organization: EducationalOrganizationModel, *, primary: bool = False) -> None:
    ParticipantOrganizationMembershipModel.objects.create(participant=participant, organization=organization, is_primary=primary)


def test_the_card_names_the_school_the_performer_comes_from() -> None:
    row = _registry_row()
    _enrol(row, _organization("ДШИ № 5"), primary=True)

    assert _educational_organizations([_participant(registry_participant_id=str(row.id))]) == ["ДШИ № 5"]


def test_the_main_school_is_printed_first() -> None:
    """Участник может состоять в двух; первым стоит то, которое он назвал основным."""
    row = _registry_row()
    _enrol(row, _organization("Áльфа"))
    _enrol(row, _organization("Гимназия № 1"), primary=True)

    assert _educational_organizations([_participant(registry_participant_id=str(row.id))])[0] == "Гимназия № 1"


def test_a_group_from_one_school_prints_it_once() -> None:
    school = _organization("ДШИ № 5")
    performers = []
    for _ in range(3):
        row = _registry_row()
        _enrol(row, school, primary=True)
        performers.append(_participant(registry_participant_id=str(row.id)))

    assert _educational_organizations(performers) == ["ДШИ № 5"]


def test_a_group_from_two_schools_prints_both() -> None:
    """Совместный номер двух школ — не ошибка данных, а обычная заявка."""
    performers = []
    for name in ("ДШИ № 5", "Гимназия № 1"):
        row = _registry_row()
        _enrol(row, _organization(name), primary=True)
        performers.append(_participant(registry_participant_id=str(row.id)))

    assert sorted(_educational_organizations(performers)) == ["Гимназия № 1", "ДШИ № 5"]


def test_a_performer_typed_by_hand_has_no_school_to_show() -> None:
    """Без ссылки на реестр учреждение негде взять, и пустое место честнее."""
    assert _educational_organizations([_participant(registry_participant_id=None)]) == []


def test_a_participant_outside_any_school_shows_nothing() -> None:
    row = _registry_row()

    assert _educational_organizations([_participant(registry_participant_id=str(row.id))]) == []


def test_a_deleted_school_stops_being_printed() -> None:
    """Реестр — источник правды: удалённое учреждение карточка не воскрешает."""
    row = _registry_row()
    school = _organization("ДШИ № 5")
    _enrol(row, school, primary=True)
    EducationalOrganizationModel.objects.filter(pk=school.id).update(deleted_at="2026-09-19T00:00:00Z")

    assert _educational_organizations([_participant(registry_participant_id=str(row.id))]) == []


def test_the_whole_application_costs_one_query(django_assert_num_queries: DjangoAssertNumQueries) -> None:
    """Карточка открывается на каждое переключение в очереди — запрос должен быть один."""
    performers = []
    for name in ("ДШИ № 5", "Гимназия № 1", "Лицей № 2"):
        row = _registry_row()
        _enrol(row, _organization(name), primary=True)
        performers.append(_participant(registry_participant_id=str(row.id)))

    with django_assert_num_queries(1):
        assert len(_educational_organizations(performers)) == 3


def test_no_registry_links_at_all_asks_the_database_nothing(django_assert_num_queries: DjangoAssertNumQueries) -> None:
    with django_assert_num_queries(0):
        assert _educational_organizations([_participant(registry_participant_id=None)]) == []


class TestThroughTheRealEdge:
    """Проверка того, чего не хватило в прошлый раз.

    Первая версия этой фичи читала снимок на заявке. Юнит-тест над ней проходил —
    снимок ведь честно разворачивался в имя, — а на экране не появлялось ничего,
    потому что снимок никто не пишет. Поэтому здесь карточка открывается той же
    ручкой, что и в кабинете, и проверяется то, что уходит на экран.
    """

    @staticmethod
    def _workspace_with_a_performer_from(school: str) -> dict[str, Any]:
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken

        from apps.applications.infrastructure.models.application import ApplicationModel
        from apps.applications.infrastructure.models.submission import SubmissionModel
        from apps.competitions.infrastructure.models import CompetitionModel
        from apps.identity.presentation.api.v1.auth import composition as identity_composition
        from apps.organization.application.dto.commands import ProvisionOwnerCommand
        from apps.organization.composition import build_provision_owner_handler
        from apps.organization.infrastructure.models import OrganizationModel

        client = APIClient()
        registration = client.post(
            "/api/v1/auth/registration",
            {"email": "organizer@example.com", "password": "V3ry$ecurePass!", "firstName": "Ольга", "lastName": "Петрова"},
            format="json",
        )
        access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
        build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"])))  # type: ignore[arg-type]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        organization_id = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").values_list("id", flat=True).first()
        assert organization_id is not None, "expected a provisioned organization"
        competition = CompetitionModel.objects.create(
            organizer_id=organization_id,
            status="PUBLISHED",
            title="Весенний фестиваль",
            season="2025/2026",
        )

        registry_row = _registry_row()
        _enrol(registry_row, _organization(school), primary=True)

        applicant_id = uuid7()
        submission = SubmissionModel.objects.create(
            competition_id=competition.id,
            applicant_id=applicant_id,
            status="SUBMITTED",
            participants=[
                {
                    "id": str(uuid7()),
                    "display_name": "Петрова Мария",
                    "first_name": "Мария",
                    "last_name": "Петрова",
                    "registry_participant_id": str(registry_row.id),
                    "member_count": 1,
                    "members": [],
                }
            ],
        )
        ApplicationModel.objects.create(
            competition_id=competition.id,
            applicant_id=applicant_id,
            status="SUBMITTED",
            submission_refs=[{"submission_id": str(submission.id), "participant_display_name": "Петрова Мария"}],
        )

        response = client.get(f"/api/v1/staff/applications/workspace?selected={submission.id}")
        assert response.status_code == 200, response.data
        workspace: dict[str, Any] = response.data["data"]
        return workspace

    def test_the_school_reaches_the_card(self) -> None:
        workspace = self._workspace_with_a_performer_from("ДШИ № 5")

        assert workspace["detail"] is not None
        assert workspace["detail"]["educationalOrganizations"] == ["ДШИ № 5"]
