"""Окно правки заявки на живом API: что закрывается вместе с приёмом.

Случай, ради которого написано: организатор остановил приём по вокалу, оставив
лист ожидания, а хореография на том же фестивале продолжает набор. Поданная
раньше заявка в вокале править себя больше не даёт — и, что не менее важно, сама
об этом говорит: ``editable`` на заявке и на номере отвечает тем же правилом,
которым эндпоинты отказывают, чтобы кнопка «Редактировать» отсутствовала, а не
вела в 409.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.base import uuid7
from apps.identity.presentation.api.v1.auth import composition as identity_composition

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_FAR_FUTURE = datetime(2100, 1, 1, tzinfo=UTC)
_LONG_PAST = datetime(2000, 1, 1, tzinfo=UTC)


def _seed(*, other_genre_open: bool) -> tuple[str, str, str]:
    """A festival with вокал and хореография; return (competition_id, вокал, хореография)."""
    from apps.competitions.infrastructure.models import CategoryModel, CompetitionModel

    competition = CompetitionModel.objects.create(organizer_id=uuid7(), status="PUBLISHED", title="Весна", season="2025/2026")
    vocal = CategoryModel.objects.create(competition=competition, name="Вокал", registration_opens_at=_LONG_PAST, registration_closes_at=_FAR_FUTURE)
    choreography = CategoryModel.objects.create(
        competition=competition,
        name="Хореография",
        registration_opens_at=_LONG_PAST,
        registration_closes_at=_FAR_FUTURE if other_genre_open else datetime(2001, 1, 1, tzinfo=UTC),
    )
    return str(competition.id), str(vocal.id), str(choreography.id)


def _upload_a_track(client: APIClient, submission_id: str) -> Any:
    return client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        {"file": SimpleUploadedFile("track.mp3", b"ID3 fake audio", content_type="audio/mpeg"), "attachmentType": "MUSIC"},
        format="multipart",
    )


def _stop_registration(nomination_id: str, *, waitlist: bool) -> None:
    """The organizer's early stop, with or without a queue behind it."""
    from apps.competitions.infrastructure.models import CategoryModel

    CategoryModel.objects.filter(pk=nomination_id).update(registration_stopped=True, waitlist_enabled=waitlist)


def _performance_body(nomination_id: str) -> dict[str, Any]:
    return {
        "title": "Весенний вальс",
        "durationSeconds": 210,
        "nominationId": nomination_id,
        "disciplineId": str(uuid7()),
        "ageCategoryId": str(uuid7()),
        "participantGroupId": str(uuid7()),
        "participationFormatId": str(uuid7()),
    }


def _place_order(client: APIClient, competition_id: str, nomination_id: str) -> tuple[str, str]:
    """An order with one number in ``nomination_id``, placed while the genre was open."""
    from apps.applications.infrastructure.models import ApplicationModel
    from apps.applications.infrastructure.models.submission import SubmissionModel

    application_id = client.post("/api/v1/applications", {"competitionId": competition_id}, format="json").data["data"]["id"]
    submission_id = str(client.post(f"/api/v1/applications/{application_id}/submissions").data["data"]["submissions"][0]["submissionId"])
    client.put(f"/api/v1/submissions/{submission_id}/performance", _performance_body(nomination_id), format="json")
    client.post(
        f"/api/v1/submissions/{submission_id}/participants",
        {"firstName": "Анна", "lastName": "Иванова", "birthDate": "2014-05-01", "gender": "FEMALE"},
        format="json",
    )
    # Приём идёт, заявка подана — остальной путь (оплата, рассмотрение) к сроку
    # правки отношения не имеет, поэтому статусы ставятся напрямую.
    SubmissionModel.objects.filter(pk=submission_id).update(status="SUBMITTED")
    ApplicationModel.objects.filter(pk=application_id).update(status="SUBMITTED")
    return application_id, submission_id


@pytest.fixture
def applicant() -> APIClient:
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "applicant@example.com", "password": _PASSWORD, "firstName": "Ольга", "lastName": "Петрова"},
        format="json",
    )
    access = identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


class TestAStoppedGenreWithAQueueBehindIt:
    """Вокал остановлен досрочно, очередь оставлена, хореография набирает."""

    @staticmethod
    def _closed_vocal_order(client: APIClient) -> tuple[str, str]:
        competition_id, vocal, _choreography = _seed(other_genre_open=True)
        application_id, submission_id = _place_order(client, competition_id, vocal)
        _stop_registration(vocal, waitlist=True)
        return application_id, submission_id

    def test_the_numbers_content_is_refused(self, applicant: APIClient) -> None:
        _application_id, submission_id = self._closed_vocal_order(applicant)

        refused = applicant.post(
            f"/api/v1/submissions/{submission_id}/participants",
            {"firstName": "Новый", "lastName": "Участник", "birthDate": "2013-01-01", "gender": "MALE"},
            format="json",
        )

        assert refused.status_code == 409, refused.data
        assert "Приём заявок закрыт" in str(refused.data["detail"])

    def test_the_number_says_so_itself(self, applicant: APIClient) -> None:
        """Карточка номера рисуется из этого ответа — в нём и должен быть ответ."""
        _application_id, submission_id = self._closed_vocal_order(applicant)

        assert applicant.get(f"/api/v1/submissions/{submission_id}").data["data"]["editable"] is False

    def test_the_order_says_so_too(self, applicant: APIClient) -> None:
        # Главное, ради чего флаг появился: кнопка «Редактировать» спрашивала
        # «открыт ли приём на фестивале», а фестиваль с остановленным вокалом и
        # работающей хореографией открыт и закрыт одновременно.
        application_id, _submission_id = self._closed_vocal_order(applicant)

        assert applicant.get(f"/api/v1/applications/{application_id}").data["data"]["editable"] is False

    def test_a_number_in_the_genre_still_open_stays_editable(self, applicant: APIClient) -> None:
        competition_id, vocal, choreography = _seed(other_genre_open=True)
        application_id, submission_id = _place_order(applicant, competition_id, choreography)
        _stop_registration(vocal, waitlist=True)

        assert applicant.get(f"/api/v1/submissions/{submission_id}").data["data"]["editable"] is True
        assert applicant.get(f"/api/v1/applications/{application_id}").data["data"]["editable"] is True


class TestWhileTheGenreIsOpen:
    def test_the_order_and_its_number_are_editable(self, applicant: APIClient) -> None:
        competition_id, vocal, _choreography = _seed(other_genre_open=True)
        application_id, submission_id = _place_order(applicant, competition_id, vocal)

        assert applicant.get(f"/api/v1/applications/{application_id}").data["data"]["editable"] is True
        assert applicant.get(f"/api/v1/submissions/{submission_id}").data["data"]["editable"] is True

    def test_a_draft_is_editable_while_any_door_is_open(self, applicant: APIClient) -> None:
        """Черновик спрашивают о фестивале: своих номеров у него может ещё не быть."""
        competition_id, vocal, _choreography = _seed(other_genre_open=False)
        application_id = applicant.post("/api/v1/applications", {"competitionId": competition_id}, format="json").data["data"]["id"]
        _stop_registration(vocal, waitlist=True)

        assert applicant.get(f"/api/v1/applications/{application_id}").data["data"]["editable"] is True


class TestFilesOutliveTheCloseOfRegistration:
    """Приём кончился — состав заморожен, файлы нет. Ради этого сроки и разведены.

    Фонограмму и видео присылают после того, как список собран: номер, попавший в
    фестиваль в последний день, всё ещё репетирует и меняет материал.
    """

    def test_the_track_is_still_accepted(self, applicant: APIClient) -> None:
        competition_id, vocal, _choreography = _seed(other_genre_open=False)
        _application_id, submission_id = _place_order(applicant, competition_id, vocal)
        _stop_registration(vocal, waitlist=False)

        accepted = _upload_a_track(applicant, submission_id)

        assert accepted.status_code == 201, accepted.data

    def test_while_the_numbers_content_is_not(self, applicant: APIClient) -> None:
        competition_id, vocal, _choreography = _seed(other_genre_open=False)
        _application_id, submission_id = _place_order(applicant, competition_id, vocal)
        _stop_registration(vocal, waitlist=False)

        refused = applicant.post(
            f"/api/v1/submissions/{submission_id}/participants",
            {"firstName": "Новый", "lastName": "Участник", "birthDate": "2013-01-01", "gender": "MALE"},
            format="json",
        )

        assert refused.status_code == 409, refused.data
