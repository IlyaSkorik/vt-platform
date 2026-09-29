"""Организатор правит заявку за участника — и об этом остаётся след.

Заявка хранит снимок данных участника, а не ссылку на них, поэтому опечатку в
фамилии можно починить прямо в ней: реестр участника при этом не трогается. Ручка
существует ради одного сценария — ошибку заметили после одобрения, когда номер уже
в программе фестиваля и «вернуть на исправление» из этого статуса нельзя.

Цена правкой не пересчитывается, и это проверяется отдельно: участнику назвали
сумму и он по ней заплатил.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.core import mail
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
)
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.notifications.infrastructure.models import NotificationKind, NotificationModel
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_APPLICANT_EMAIL = "applicant@example.com"
_REGISTRY_ID = "0192f000-0000-7000-8000-000000000001"


def _register(client: APIClient, email: str, first_name: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": first_name, "lastName": "Петрова"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return access


@pytest.fixture
def staff_client() -> APIClient:
    client = APIClient()
    access = _register(client, "organizer@example.com", "Ольга")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"])))  # type: ignore[arg-type]
    return client


@pytest.fixture
def applicant_id(staff_client: APIClient) -> uuid.UUID:
    client = APIClient()
    access = _register(client, _APPLICANT_EMAIL, "Мария")
    return uuid.UUID(str(AccessToken(access)["user_id"]))  # type: ignore[arg-type]


class _Festival:
    """Фестиваль со справочником — правка ссылается на те же строки, что и подача."""

    def __init__(self) -> None:
        organization_id = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").values_list("id", flat=True).first()
        assert organization_id is not None, "expected a provisioned organization"
        self.competition = CompetitionModel.objects.create(
            organizer_id=organization_id,
            status="PUBLISHED",
            title="Весенний фестиваль",
            season="2025/2026",
        )
        self.nomination = CategoryModel.objects.create(competition=self.competition, name="Вокал")
        self.other_nomination = CategoryModel.objects.create(competition=self.competition, name="Хореография")
        self.discipline = DisciplineModel.objects.create(competition=self.competition, category_id=self.nomination.id, name="Эстрадный вокал")
        self.group = ParticipantGroupModel.objects.create(competition=self.competition, name="Соло", min_count=1, max_count=1)
        self.age = AgeCategoryModel.objects.create(
            competition=self.competition,
            participant_group_id=self.group.id,
            name="7-9 лет",
            min_age=7,
            max_age=9,
        )
        self.older = AgeCategoryModel.objects.create(
            competition=self.competition,
            participant_group_id=self.group.id,
            name="10-12 лет",
            min_age=10,
            max_age=12,
        )
        self.format = ParticipationFormatModel.objects.create(competition=self.competition, name="Очно")

    def performance_json(self) -> dict[str, Any]:
        return {
            "title": "Лебединое озеро",
            "duration_seconds": 210,
            "nomination_id": str(self.nomination.id),
            "discipline_id": str(self.discipline.id),
            "age_category_id": str(self.age.id),
            "participant_group_id": str(self.group.id),
            "participation_format_id": str(self.format.id),
            "comment": "",
            "age_composition": "",
        }

    def performance_payload(self, **overrides: Any) -> dict[str, Any]:
        payload = {
            "title": "Лебединое озеро",
            "durationSeconds": 210,
            "nominationId": str(self.nomination.id),
            "disciplineId": str(self.discipline.id),
            "ageCategoryId": str(self.age.id),
            "participantGroupId": str(self.group.id),
            "participationFormatId": str(self.format.id),
            "comment": "",
            "ageComposition": "",
        }
        payload.update(overrides)
        return payload


def _entry(
    festival: _Festival,
    applicant_id: uuid.UUID,
    *,
    status: str = "SCHEDULED",
) -> tuple[ApplicationModel, SubmissionModel]:
    """Одна заявка с одним номером, солисткой из реестра и педагогом."""
    submission = SubmissionModel.objects.create(
        competition_id=festival.competition.id,
        applicant_id=applicant_id,
        status=status,
        performance=festival.performance_json(),
        participants=[
            {
                "id": "0192f000-0000-7000-8000-0000000000aa",
                "display_name": "Иванва Анна",
                "first_name": "Анна",
                "last_name": "Иванва",
                "middle_name": None,
                "birth_date": "2016-05-12",
                "gender": "FEMALE",
                "registry_participant_id": _REGISTRY_ID,
                "member_count": 1,
                "members": [],
            }
        ],
        teachers=[
            {
                "id": "0192f000-0000-7000-8000-0000000000bb",
                "first_name": "Ольга",
                "last_name": "Петрова",
                "middle_name": None,
                "role": "Педагог",
                "directory_teacher_id": None,
            }
        ],
        price_snapshot={"amount": "1500.00", "currency": "BYN", "calculated_at": "2026-07-10T00:00:00+00:00"},
    )
    application = ApplicationModel.objects.create(
        competition_id=festival.competition.id,
        applicant_id=applicant_id,
        status="SUBMITTED",
        submission_refs=[{"submission_id": str(submission.id), "participant_display_name": "Иванва Анна"}],
    )
    return application, submission


def _correct(client: APIClient, submission_id: uuid.UUID, payload: dict[str, Any]) -> Any:
    return client.put(f"/api/v1/staff/applications/{submission_id}/content", payload, format="json")


def _fixed_participant(**overrides: Any) -> dict[str, Any]:
    entry = {
        "id": "0192f000-0000-7000-8000-0000000000aa",
        "firstName": "Анна",
        "lastName": "Иванова",
        "middleName": None,
        "birthDate": "2016-05-12",
        "gender": "FEMALE",
        "memberCount": 1,
        "members": [],
    }
    entry.update(overrides)
    return entry


class TestCorrectingAnEntryPastTheFreeze:
    def test_a_surname_is_fixed_on_an_entry_already_in_the_programme(
        self, staff_client: APIClient, applicant_id: uuid.UUID
    ) -> None:
        """Ровно тот случай, ради которого ручка и сделана: номер уже на фестивале,
        а на дипломе будет напечатана фамилия с ошибкой."""
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        response = _correct(staff_client, submission.id, {"participants": [_fixed_participant()]})

        assert response.status_code == 200, response.data
        submission.refresh_from_db()
        assert [p["display_name"] for p in submission.participants] == ["Иванова Анна"]
        assert submission.status == "SCHEDULED"

    def test_the_registry_link_survives_the_correction(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """Заявка несёт снимок карточки из реестра. Исправляется снимок — связь с
        карточкой остаётся, иначе учреждение выступающей пропадёт из очереди."""
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        _correct(staff_client, submission.id, {"participants": [_fixed_participant()]})

        submission.refresh_from_db()
        assert submission.participants[0]["registry_participant_id"] == _REGISTRY_ID

    def test_the_frozen_price_is_left_alone(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id, status="PAID")

        _correct(
            staff_client,
            submission.id,
            {"performance": festival.performance_payload(ageCategoryId=str(festival.older.id))},
        )

        submission.refresh_from_db()
        assert submission.price_snapshot["amount"] == "1500.00"

    def test_the_performance_is_corrected_together_with_its_categories(
        self, staff_client: APIClient, applicant_id: uuid.UUID
    ) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        response = _correct(
            staff_client,
            submission.id,
            {"performance": festival.performance_payload(title="Лебединое озеро (фрагмент)", durationSeconds=180)},
        )

        assert response.status_code == 200, response.data
        submission.refresh_from_db()
        assert submission.performance["title"] == "Лебединое озеро (фрагмент)"
        assert submission.performance["duration_seconds"] == 180

    def test_a_teacher_can_be_credited_afterwards(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        _correct(
            staff_client,
            submission.id,
            {
                "teachers": [
                    {"id": "0192f000-0000-7000-8000-0000000000bb", "firstName": "Ольга", "lastName": "Петрова", "role": "Педагог"},
                    {"firstName": "Игорь", "lastName": "Сидоров", "role": "Концертмейстер"},
                ]
            },
        )

        submission.refresh_from_db()
        assert sorted(t["last_name"] for t in submission.teachers) == ["Петрова", "Сидоров"]

    def test_a_section_left_out_of_the_body_is_left_alone(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """Форма, открытая на вкладке «Выступление», не должна вычистить педагогов."""
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        _correct(staff_client, submission.id, {"performance": festival.performance_payload(title="Другое название")})

        submission.refresh_from_db()
        assert len(submission.teachers) == 1
        assert len(submission.participants) == 1


class TestTheCorrectionIsNeverSilent:
    def test_the_applicant_gets_a_letter_saying_what_moved(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        application, submission = _entry(festival, applicant_id)
        mail.outbox.clear()

        _correct(staff_client, submission.id, {"participants": [_fixed_participant()]}, )

        assert len(mail.outbox) == 1
        letter = mail.outbox[0]
        assert letter.to == [_APPLICANT_EMAIL]
        assert str(application.id)[:8].upper() in letter.subject
        assert "Иванва Анна → Иванова Анна" in letter.body

    def test_the_letter_carries_the_organizers_reason_when_given(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)
        mail.outbox.clear()

        _correct(
            staff_client,
            submission.id,
            {"participants": [_fixed_participant()], "comment": "Сверили со свидетельством о рождении."},
        )

        assert "Сверили со свидетельством о рождении." in mail.outbox[0].body

    def test_the_cabinet_says_the_same_thing(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        application, submission = _entry(festival, applicant_id)

        _correct(staff_client, submission.id, {"participants": [_fixed_participant()]})

        entry = NotificationModel.objects.get(recipient_id=applicant_id)
        assert entry.kind == NotificationKind.APPLICATION_CORRECTED
        assert entry.link == f"/cabinet/applications/{application.id}"

    def test_the_entry_keeps_its_own_record_of_being_corrected(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """История карточки должна отвечать «кто и что поменял», а не только «что
        стало» — иначе спор с участником разрешить нечем."""
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        _correct(staff_client, submission.id, {"participants": [_fixed_participant()]})

        submission.refresh_from_db()
        assert len(submission.organizer_edits) == 1
        record = submission.organizer_edits[0]
        assert record["created_by"]
        assert any("Иванова Анна" in line for line in record["changes"])

    def test_the_taxonomy_change_is_named_not_numbered(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """Строка «Возрастная категория: <uuid> → <uuid>» бесполезна и участнику,
        и организатору."""
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        response = _correct(
            staff_client,
            submission.id,
            {"performance": festival.performance_payload(ageCategoryId=str(festival.older.id))},
        )

        assert response.data["data"]["changes"] == ["Возрастная категория: 7-9 лет → 10-12 лет"]

    def test_saving_an_untouched_form_tells_nobody_anything(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)
        mail.outbox.clear()

        response = _correct(staff_client, submission.id, {"performance": festival.performance_payload()})

        assert response.status_code == 200, response.data
        assert response.data["data"]["changes"] == []
        assert mail.outbox == []
        assert NotificationModel.objects.count() == 0
        submission.refresh_from_db()
        assert submission.organizer_edits == []


class TestWhoAndWhenItIsRefused:
    def test_a_completed_entry_is_refused(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id, status="COMPLETED")

        response = _correct(staff_client, submission.id, {"participants": [_fixed_participant()]})

        assert response.status_code in {409, 422}, response.data
        submission.refresh_from_db()
        assert submission.participants[0]["last_name"] == "Иванва"

    def test_a_cancelled_entry_is_refused(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id, status="CANCELLED")

        response = _correct(staff_client, submission.id, {"participants": [_fixed_participant()]})

        assert response.status_code in {409, 422}, response.data

    def test_someone_who_is_not_staff_cannot_correct_anybodys_entry(self, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)
        outsider = APIClient()
        _register(outsider, "outsider@example.com", "Пётр")

        response = _correct(outsider, submission.id, {"participants": [_fixed_participant()]})

        assert response.status_code == 403, response.data

    def test_an_empty_body_is_refused_rather_than_silently_accepted(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        response = _correct(staff_client, submission.id, {"comment": "просто так"})

        assert response.status_code == 400, response.data


class TestTheCardCarriesWhatTheFormNeeds:
    def test_the_workspace_hands_over_the_festivals_own_options(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        response = staff_client.get(f"/api/v1/staff/applications/workspace?selected={submission.id}")

        taxonomy = response.data["data"]["detail"]["taxonomy"]
        assert {option["name"] for option in taxonomy["nominations"]} == {"Вокал", "Хореография"}
        assert taxonomy["disciplines"][0]["nominationId"] == str(festival.nomination.id)
        assert taxonomy["ageCategories"][0]["participantGroupId"] == str(festival.group.id)

    def test_the_card_says_whether_the_entry_can_still_be_corrected(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        festival = _Festival()
        _, submission = _entry(festival, applicant_id, status="COMPLETED")

        response = staff_client.get(f"/api/v1/staff/applications/workspace?selected={submission.id}")

        assert response.data["data"]["detail"]["performances"][0]["canEditContent"] is False

    def test_the_card_hands_over_the_performers_own_fields(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        # Форму исправления нельзя заполнить из склеенной строки «Фамилия Имя».
        festival = _Festival()
        _, submission = _entry(festival, applicant_id)

        response = staff_client.get(f"/api/v1/staff/applications/workspace?selected={submission.id}")

        performer = response.data["data"]["detail"]["performances"][0]["participants"][0]
        assert performer["lastName"] == "Иванва"
        assert performer["birthDate"] == "2016-05-12"
