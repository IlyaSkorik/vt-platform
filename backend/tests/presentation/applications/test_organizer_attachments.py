"""Организатор прикладывает к номеру фонограмму за участника.

Сценарий один и тот же каждый фестиваль: трек приходит в сообщении, на флешке перед
репетицией или письмом утром — то есть мимо формы и после того, как приём закрылся.
Раньше это кончалось просьбой «зайдите в кабинет и загрузите сами»; теперь файл
кладёт туда организатор, прямо из карточки заявки.

Что здесь проверяется, кроме самой загрузки: что календарь загрузке не мешает (ради
этого ручка и сделана), что ограничения на формат и размер при этом остаются, что
чужой в неё не попадает — и что след остаётся в истории заявки.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
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
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


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
def outsider_client(staff_client: APIClient) -> APIClient:
    """Зарегистрированный человек без отношения к организации."""
    client = APIClient()
    _register(client, "outsider@example.com", "Пётр")
    return client


@pytest.fixture
def applicant(staff_client: APIClient) -> tuple[APIClient, uuid.UUID]:
    client = APIClient()
    access = _register(client, "applicant@example.com", "Мария")
    return client, uuid.UUID(str(AccessToken(access)["user_id"]))  # type: ignore[arg-type]


@pytest.fixture
def applicant_id(applicant: tuple[APIClient, uuid.UUID]) -> uuid.UUID:
    return applicant[1]


class _Festival:
    def __init__(self) -> None:
        organization_id = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").values_list("id", flat=True).first()
        assert organization_id is not None
        self.competition = CompetitionModel.objects.create(
            organizer_id=organization_id,
            status="PUBLISHED",
            title="Весенний фестиваль",
            season="2025/2026",
            # Срок загрузки фонограмм прошёл — ровно то состояние, в котором трек и
            # приносят организатору «на флешке».
            deadline_music_upload="2026-01-01T00:00:00+00:00",
        )
        self.nomination = CategoryModel.objects.create(competition=self.competition, name="Вокал")
        self.discipline = DisciplineModel.objects.create(competition=self.competition, category_id=self.nomination.id, name="Эстрадный вокал")
        self.group = ParticipantGroupModel.objects.create(competition=self.competition, name="Соло", min_count=1, max_count=1)
        self.age = AgeCategoryModel.objects.create(
            competition=self.competition,
            participant_group_id=self.group.id,
            name="7-9 лет",
            min_age=7,
            max_age=9,
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


def _entry(festival: _Festival, applicant_id: uuid.UUID, *, status: str = "SCHEDULED") -> SubmissionModel:
    submission = SubmissionModel.objects.create(
        competition_id=festival.competition.id,
        applicant_id=applicant_id,
        status=status,
        performance=festival.performance_json(),
        participants=[
            {
                "id": "0192f000-0000-7000-8000-0000000000aa",
                "display_name": "Иванова Анна",
                "first_name": "Анна",
                "last_name": "Иванова",
                "middle_name": None,
                "birth_date": "2016-05-12",
                "gender": "FEMALE",
                "member_count": 1,
                "members": [],
            }
        ],
        teachers=[],
    )
    ApplicationModel.objects.create(
        competition_id=festival.competition.id,
        applicant_id=applicant_id,
        status="SUBMITTED",
        submission_refs=[{"submission_id": str(submission.id), "participant_display_name": "Иванова Анна"}],
    )
    return submission


def _upload(client: APIClient, submission_id: uuid.UUID, file: SimpleUploadedFile, kind: str = "MUSIC") -> Any:
    return client.post(
        f"/api/v1/staff/applications/{submission_id}/attachments",
        {"file": file, "attachmentType": kind},
        format="multipart",
    )


def _track(name: str = "katyusha.mp3") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"ID3 not really audio but enough", content_type="audio/mpeg")


class TestTheOrganizerAttachesAFile:
    def test_a_phonogram_is_attached_after_registration_has_closed(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """Тот самый случай: приём закрыт, номер уже в программе, трек прислали вчера."""
        submission = _entry(_Festival(), applicant_id)

        response = _upload(staff_client, submission.id, _track())

        assert response.status_code == 201, response.data
        assert [a["type"] for a in response.data["data"]["attachments"]] == ["MUSIC"]
        submission.refresh_from_db()
        assert [a["type"] for a in submission.attachments] == ["MUSIC"]

    def test_the_upload_is_written_into_the_entrys_history(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """Чужую заявку правят — значит, видно, кто и что приложил."""
        submission = _entry(_Festival(), applicant_id)

        _upload(staff_client, submission.id, _track())

        submission.refresh_from_db()
        assert [entry["changes"] for entry in submission.organizer_edits] == [["Загружен файл (фонограмма): katyusha.mp3"]]

    def test_a_format_the_festival_does_not_accept_is_refused(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """Срок организатору не писан, а формат — писан: его играет зал, а не календарь."""
        submission = _entry(_Festival(), applicant_id)

        response = _upload(staff_client, submission.id, SimpleUploadedFile("track.exe", b"nope", content_type="application/octet-stream"))

        assert response.status_code == 415
        submission.refresh_from_db()
        assert submission.attachments == []

    def test_an_attached_file_can_be_taken_off_again(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """Иначе присланный дважды трек нечем заменить, а играет тот, что остался."""
        submission = _entry(_Festival(), applicant_id)
        attachment_id = _upload(staff_client, submission.id, _track()).data["data"]["attachments"][0]["id"]

        response = staff_client.delete(f"/api/v1/staff/applications/{submission.id}/attachments/{attachment_id}")

        assert response.status_code == 200, response.data
        assert response.data["data"]["attachments"] == []
        submission.refresh_from_db()
        assert submission.attachments == []

    def test_an_outsider_cannot_attach_anything(self, outsider_client: APIClient, applicant_id: uuid.UUID) -> None:
        submission = _entry(_Festival(), applicant_id)

        assert _upload(outsider_client, submission.id, _track()).status_code == 403

    def test_the_applicant_is_still_past_their_own_deadline(self, staff_client: APIClient, applicant: tuple[APIClient, uuid.UUID]) -> None:
        """Разница настоящая, а не «срок просто не наступил».

        Один и тот же файл, одна и та же заявка, одна и та же минута: участнику
        отказывают, организатору — нет. Иначе тест выше доказывал бы только то, что
        фестиваль ничего не ограничивает.
        """
        applicant_client, applicant_user_id = applicant
        submission = _entry(_Festival(), applicant_user_id)

        refused = applicant_client.post(
            f"/api/v1/submissions/{submission.id}/attachments",
            {"file": _track(), "attachmentType": "MUSIC"},
            format="multipart",
        )

        assert refused.status_code == 409, refused.data
        assert _upload(staff_client, submission.id, _track()).status_code == 201


class TestWhatTheCardSaysTheEntryAccepts:
    def test_the_card_states_the_same_upload_rules_the_applicant_was_held_to(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """Организатор догружает то же, что мог участник, — значит, и правила те же."""
        festival = _Festival()
        submission = _entry(festival, applicant_id)

        workspace = staff_client.get(f"/api/v1/staff/applications/workspace?selected={submission.id}")

        assert workspace.status_code == 200, workspace.data
        performance = workspace.data["data"]["detail"]["performances"][0]
        # Форму участия организатор не настраивал — значит, по ней ничего и не просят.
        assert performance["uploadRequirement"] is None
