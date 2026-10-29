"""Где заканчивается «Одобрить» — и куда после этого ложится номер.

Кнопка одобрения прогоняет номер через весь платёжный хвост за один запрос, и
раньше доводила его до ``SCHEDULED``. Из-за этого статус, который должен значить
«стоит в программе», выставлялся в ту же миллисекунду, что и ``ACCEPTED``, —
то есть не значил ничего: одобренный номер читался как назначенный, даже если его
никто никуда не ставил. Теперь цепочка останавливается на ``ACCEPTED``, а
``SCHEDULED`` ставит контекст программ, когда номер действительно получает место.

У правки есть вторая половина, без которой она ломает рабочий стол: очередь для
``ACCEPTED`` считалась по квитанции, и одобренный номер падал бы обратно в «ждут
оплату». Поэтому здесь же закреплено, куда он попадает.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.base import uuid7
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.applications.presentation.api.v1.organizer.support import _queue_for
from apps.competitions.infrastructure.models import CompetitionModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


def _register(client: APIClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Ольга", "lastName": "Петрова"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return access


@pytest.fixture
def staff_client() -> APIClient:
    client = APIClient()
    access = _register(client, "organizer@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"])))  # type: ignore[arg-type]
    return client


def _festival() -> uuid.UUID:
    organization_id = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").values_list("id", flat=True).first()
    assert organization_id is not None, "expected a provisioned organization"
    competition = CompetitionModel.objects.create(
        organizer_id=organization_id,
        status="PUBLISHED",
        title="Весенний фестиваль",
        season="2025/2026",
    )
    return competition.id


def _order(*, competition_id: uuid.UUID, performances: int = 1) -> list[SubmissionModel]:
    """Поданный заказ с `performances` номерами, ждущими решения организатора."""
    # v7 и не иначе: ``UserId`` отказывает любой другой версии, и фикстура с uuid4
    # падает не на том, что проверяет тест.
    applicant_id = uuid7()
    submissions = [
        SubmissionModel.objects.create(competition_id=competition_id, applicant_id=applicant_id, status="SUBMITTED") for _ in range(performances)
    ]
    ApplicationModel.objects.create(
        competition_id=competition_id,
        applicant_id=applicant_id,
        status="SUBMITTED",
        submission_refs=[{"submission_id": str(s.id), "participant_display_name": "Иванова Анна"} for s in submissions],
    )
    return submissions


def _approve(client: APIClient, submission_id: uuid.UUID) -> Any:
    return client.post(f"/api/v1/staff/applications/{submission_id}/actions/approve", {}, format="json")


class TestWhereApprovalStops:
    def test_an_approved_entry_is_accepted_and_not_scheduled(self, staff_client: APIClient) -> None:
        submissions = _order(competition_id=_festival())

        response = _approve(staff_client, submissions[0].id)

        assert response.status_code == 200, response.data
        submissions[0].refresh_from_db()
        assert submissions[0].status == "ACCEPTED"

    def test_every_entry_of_the_order_stops_in_the_same_place(self, staff_client: APIClient) -> None:
        # Одобрение применяется ко всему заказу разом, а не к одному номеру.
        submissions = _order(competition_id=_festival(), performances=3)

        _approve(staff_client, submissions[0].id)

        for submission in submissions:
            submission.refresh_from_db()
            assert submission.status == "ACCEPTED"

    def test_the_answer_names_the_status_it_actually_left_behind(self, staff_client: APIClient) -> None:
        # Экран перерисовывает кнопки по этому полю, и статус из ответа, разошедшийся
        # с базой, показал бы организатору действия, которых уже нет.
        submissions = _order(competition_id=_festival())

        response = _approve(staff_client, submissions[0].id)

        assert response.data["data"]["status"] == "ACCEPTED"
        assert [action["key"] for action in response.data["data"]["capabilities"]] == ["move_to_running", "cancel"]

    def test_the_payment_tail_is_still_walked_in_full(self, staff_client: APIClient) -> None:
        # Остановка на ACCEPTED не означает пропуска шагов: номер по-прежнему
        # проходит APPROVED → WAITING_PAYMENT → PAID, и история это помнит. На ней
        # считается период в финансовой сводке.
        submissions = _order(competition_id=_festival())

        _approve(staff_client, submissions[0].id)

        submissions[0].refresh_from_db()
        walked = [row["to_status"] for row in submissions[0].status_history]
        assert walked == ["UNDER_REVIEW", "APPROVED", "WAITING_PAYMENT", "PAID", "ACCEPTED"]
        assert "SCHEDULED" not in walked


class TestWhichPileItLandsIn:
    """Очередь — это рабочая стопка организатора, и после правки она не должна поехать."""

    def test_an_accepted_entry_is_ready_for_the_festival(self) -> None:
        # Без этого правила ACCEPTED считался бы по квитанции и улетал в «ждут
        # оплату» сразу после одобрения — при том что ту же цепочку он прошёл
        # оплаченным.
        assert _queue_for("ACCEPTED", has_receipts=False) == "READY"
        assert _queue_for("ACCEPTED", has_receipts=True) == "READY"

    def test_an_entry_in_a_programme_is_on_the_festival(self) -> None:
        assert _queue_for("SCHEDULED", has_receipts=False) == "RUNNING"

    def test_an_entry_still_awaiting_payment_is_where_it_was(self) -> None:
        # Статусы до принятия по-прежнему делятся квитанцией — это не трогали.
        assert _queue_for("PAID", has_receipts=False) == "WAITING_PAYMENT"
        assert _queue_for("PAID", has_receipts=True) == "READY"
