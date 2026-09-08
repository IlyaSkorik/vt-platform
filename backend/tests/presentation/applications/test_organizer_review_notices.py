"""Telling the applicant what the organizer decided about their order.

A return for correction already wrote to them; an approval did not, and that is the
outcome they cannot discover by refreshing — the order simply stops being "on
review". These tests cover the letter, the cabinet entry and the journal line the
approve action leaves behind.
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
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.notifications.infrastructure.models import NotificationKind, NotificationModel
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_APPLICANT_EMAIL = "applicant@example.com"


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
    """A real Identity user, because the notice is addressed to their stored email."""
    client = APIClient()
    access = _register(client, _APPLICANT_EMAIL, "Мария")
    return uuid.UUID(str(AccessToken(access)["user_id"]))  # type: ignore[arg-type]


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


def _order(*, competition_id: uuid.UUID, applicant_id: uuid.UUID, performances: int = 1) -> tuple[ApplicationModel, list[SubmissionModel]]:
    """One submitted order with `performances` entries awaiting the organizer's decision."""
    submissions = [
        SubmissionModel.objects.create(
            competition_id=competition_id,
            applicant_id=applicant_id,
            status="SUBMITTED",
        )
        for _ in range(performances)
    ]
    application = ApplicationModel.objects.create(
        competition_id=competition_id,
        applicant_id=applicant_id,
        status="SUBMITTED",
        submission_refs=[{"submission_id": str(s.id), "participant_display_name": "Иванова Анна"} for s in submissions],
    )
    return application, submissions


def _approve(client: APIClient, submission_id: uuid.UUID) -> Any:
    return client.post(f"/api/v1/staff/applications/{submission_id}/actions/approve", {}, format="json")


class TestApprovalIsTold:
    def test_the_applicant_gets_a_letter_naming_their_order(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        application, submissions = _order(competition_id=_festival(), applicant_id=applicant_id)
        mail.outbox.clear()

        response = _approve(staff_client, submissions[0].id)

        assert response.status_code == 200, response.data
        assert len(mail.outbox) == 1
        letter = mail.outbox[0]
        assert letter.to == [_APPLICANT_EMAIL]
        number = str(application.id)[:8].upper()
        assert letter.subject == f"Заявка #{number} одобрена организатором"
        assert "Весенний фестиваль" in letter.body
        assert "Мария" in letter.body

    def test_the_letter_counts_every_performance_the_order_carries(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        # Approving reaches the whole order, so the notice must not describe one entry.
        _, submissions = _order(competition_id=_festival(), applicant_id=applicant_id, performances=3)
        mail.outbox.clear()

        _approve(staff_client, submissions[0].id)

        assert "Одобрено выступлений: 3." in mail.outbox[0].body

    def test_the_cabinet_says_the_same_thing(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        """A letter can be filtered or sent to an address nobody reads; the feed is
        where the applicant looks when they suspect they missed something."""
        application, submissions = _order(competition_id=_festival(), applicant_id=applicant_id)

        _approve(staff_client, submissions[0].id)

        entry = NotificationModel.objects.get(recipient_id=applicant_id)
        assert entry.kind == NotificationKind.APPLICATION_APPROVED
        assert str(application.id)[:8].upper() in entry.title
        assert entry.link == f"/cabinet/applications/{application.id}"

    def test_the_journal_records_that_the_applicant_was_written_to(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        _, submissions = _order(competition_id=_festival(), applicant_id=applicant_id, performances=2)

        _approve(staff_client, submissions[0].id)

        for submission in submissions:
            submission.refresh_from_db()
            assert any("одобрена организатором" in entry["text"] for entry in submission.participant_messages)

    def test_nothing_is_sent_when_there_was_nothing_to_approve(self, staff_client: APIClient, applicant_id: uuid.UUID) -> None:
        # The action refuses an order already past review; a letter here would announce
        # a decision the organizer did not just make.
        _, submissions = _order(competition_id=_festival(), applicant_id=applicant_id)
        SubmissionModel.objects.filter(id=submissions[0].id).update(status="CANCELLED")
        mail.outbox.clear()

        response = _approve(staff_client, submissions[0].id)

        assert response.status_code == 409
        assert mail.outbox == []
        assert NotificationModel.objects.count() == 0
