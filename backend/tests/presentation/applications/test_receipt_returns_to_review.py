"""Замена квитанции выводит заявку из статуса «на доработке».

Не ту квитанцию прикладывают часто — от другого фестиваля, на другую сумму, чужой
перевод, — и организатор возвращает заявку на доработку. Но квитанция лежит на
заказе, а «на доработке» — на выступлениях, и до этой правки замена квитанции не
меняла ровным счётом ничего из того, что видит организатор.

Выхода не было ни с одной стороны: у участника нет своей «подать заново» (подача
заказа отправляет только черновики), а организатору в статусе REQUIRES_CORRECTION
не предлагается ни одного действия. Заявка оставалась в очереди «На доработке»
навсегда.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.base import uuid7
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.competitions.infrastructure.models.rules import AdmissionRuleModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
)
from apps.identity.presentation.api.v1.auth import composition as identity_composition

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


def _applicant() -> tuple[APIClient, uuid.UUID]:
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "applicant@example.com", "password": _PASSWORD, "firstName": "Мария", "lastName": "Петрова"},
        format="json",
    )
    user_id = registration.data["data"]["id"]
    access = identity_composition.build_token_service().issue(subject=user_id).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client, uuid.UUID(user_id)


class _Festival:
    """Фестиваль, принимающий ровно одно сочетание — иначе номер не подать заново."""

    def __init__(self) -> None:
        self.competition = CompetitionModel.objects.create(
            organizer_id=uuid7(),
            status="PUBLISHED",
            title="Весенний фестиваль",
            season="2025/2026",
        )
        self.nomination = CategoryModel.objects.create(
            competition=self.competition,
            name="Вокал",
            registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
            registration_closes_at=datetime(2100, 1, 1, tzinfo=UTC),
        )
        self.discipline = DisciplineModel.objects.create(competition=self.competition, category_id=self.nomination.id, name="Эстрадный вокал")
        self.group = ParticipantGroupModel.objects.create(competition=self.competition, name="Соло", min_count=1, max_count=1)
        self.age = AgeCategoryModel.objects.create(
            competition=self.competition, participant_group_id=self.group.id, name="7-9 лет", min_age=7, max_age=9
        )
        self.format = ParticipationFormatModel.objects.create(competition=self.competition, name="Очно")
        AdmissionRuleModel.objects.create(
            competition=self.competition,
            category_id=self.nomination.id,
            discipline_id=self.discipline.id,
            age_category_id=self.age.id,
            participant_group_id=self.group.id,
            participation_format_id=self.format.id,
        )

    def performance(self) -> dict[str, Any]:
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


def _returned_order(
    festival: _Festival,
    applicant_id: uuid.UUID,
    *,
    performance: dict[str, Any] | None = None,
) -> tuple[ApplicationModel, SubmissionModel]:
    """Поданный заказ с одним номером, возвращённым организатором на доработку."""
    submission = SubmissionModel.objects.create(
        competition_id=festival.competition.id,
        applicant_id=applicant_id,
        status="REQUIRES_CORRECTION",
        performance=festival.performance() if performance is None else performance,
        participants=[
            {
                "id": str(uuid7()),
                "display_name": "Иванова Анна",
                "first_name": "Анна",
                "last_name": "Иванова",
                "middle_name": None,
                "birth_date": "2018-05-12",
                "gender": "FEMALE",
                "registry_participant_id": None,
                "member_count": 1,
                "members": [],
            }
        ],
        teachers=[
            {
                "id": str(uuid7()),
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
        submission_refs=[
            {
                "submission_id": str(submission.id),
                "performance_title": "Лебединое озеро",
                "participant_display_name": "Иванова Анна",
                "nomination": "Вокал",
                "discipline": "Эстрадный вокал",
                "status": "REQUIRES_CORRECTION",
                "price": {"amount": "1500.00", "currency": "BYN", "calculated_at": "2026-07-10T00:00:00+00:00"},
            }
        ],
    )
    return application, submission


def _upload(client: APIClient, application_id: Any, name: str = "receipt.pdf") -> Any:
    upload = SimpleUploadedFile(name, b"%PDF-1.4 paid", content_type="application/pdf")
    return client.post(f"/api/v1/applications/{application_id}/receipts", {"file": upload}, format="multipart")


class TestTheRightReceiptEndsTheCorrection:
    def test_attaching_one_puts_the_entry_back_in_the_queue(self) -> None:
        client, applicant_id = _applicant()
        festival = _Festival()
        application, submission = _returned_order(festival, applicant_id)

        response = _upload(client, application.id)

        assert response.status_code == 200, response.data
        submission.refresh_from_db()
        assert submission.status == "SUBMITTED"

    def test_the_transition_is_recorded_so_the_organizer_can_see_why_it_came_back(self) -> None:
        # История карточки — единственное место, где видно, что заявка вернулась
        # сама, а не была подана заново.
        client, applicant_id = _applicant()
        festival = _Festival()
        application, submission = _returned_order(festival, applicant_id)

        _upload(client, application.id)

        submission.refresh_from_db()
        assert ("REQUIRES_CORRECTION", "SUBMITTED") in [(entry.get("from_status"), entry.get("to_status")) for entry in submission.status_history]

    def test_the_orders_cached_status_stops_saying_correction(self) -> None:
        """Кабинет читает снимок статуса на заказе, а не сам номер: без обновления
        снимка плашка «на доработке» пережила бы саму доработку."""
        client, applicant_id = _applicant()
        festival = _Festival()
        application, _ = _returned_order(festival, applicant_id)

        response = _upload(client, application.id)

        assert [ref["status"] for ref in response.data["data"]["submissions"]] == ["SUBMITTED"]
        application.refresh_from_db()
        assert [ref["status"] for ref in application.submission_refs] == ["SUBMITTED"]


class TestWhatItDoesNotDo:
    def test_taking_a_receipt_back_leaves_the_correction_alone(self) -> None:
        # Снятая квитанция — это отсутствие доказательства оплаты, а не исправление.
        client, applicant_id = _applicant()
        festival = _Festival()
        application, submission = _returned_order(festival, applicant_id)
        uploaded = _upload(client, application.id)
        receipt_id = uploaded.data["data"]["paymentReceipts"][0]["id"]
        SubmissionModel.objects.filter(id=submission.id).update(status="REQUIRES_CORRECTION")

        removed = client.delete(f"/api/v1/applications/{application.id}/receipts/{receipt_id}")

        assert removed.status_code == 200, removed.data
        submission.refresh_from_db()
        assert submission.status == "REQUIRES_CORRECTION"

    def test_an_entry_that_cannot_pass_its_own_checks_stays_put(self) -> None:
        """Вернуться в очередь значит «это снова можно смотреть», и решает это домен.
        Номер без заполненного выступления не подаётся и квитанцией не чинится."""
        client, applicant_id = _applicant()
        festival = _Festival()
        application, submission = _returned_order(festival, applicant_id)
        SubmissionModel.objects.filter(id=submission.id).update(performance=None)

        response = _upload(client, application.id)

        assert response.status_code == 200, response.data
        submission.refresh_from_db()
        assert submission.status == "REQUIRES_CORRECTION"

    def test_an_entry_nobody_returned_is_not_touched(self) -> None:
        client, applicant_id = _applicant()
        festival = _Festival()
        application, submission = _returned_order(festival, applicant_id)
        SubmissionModel.objects.filter(id=submission.id).update(status="APPROVED")

        _upload(client, application.id)

        submission.refresh_from_db()
        assert submission.status == "APPROVED"
