"""Integration tests for telling the organizer that a placed order was edited.

Covers the whole path the feature adds: an edit made through the applicant's own API
is journalled only once the order has been submitted, the sweep folds an editing
session into one letter, and a letter already sent is never sent twice.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.applications.infrastructure.models import ApplicationModel, ApplicationRevisionModel
from apps.applications.infrastructure.models.base import uuid7
from apps.applications.tasks import notify_application_revisions
from apps.identity.presentation.api.v1.auth import composition as identity_composition

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_ORGANIZER_EMAIL = "festival-office@example.com"


def _seed_open_competition() -> str:
    """A published competition with one open nomination, run by an organization we can email."""
    from apps.competitions.infrastructure.models import CategoryModel, CompetitionModel
    from apps.organization.infrastructure.models.organization import OrganizationModel

    organization = OrganizationModel.objects.create(name="Дом культуры", slug=f"dk-{uuid7().hex[:8]}", email=_ORGANIZER_EMAIL)
    competition = CompetitionModel.objects.create(
        organizer_id=organization.id,
        status="PUBLISHED",
        title="Весенний фестиваль",
        season="2025/2026",
    )
    CategoryModel.objects.create(
        competition=competition,
        name="Вокал",
        registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
        registration_closes_at=datetime(2100, 1, 1, tzinfo=UTC),
    )
    return str(competition.id)


def _auth(email: str) -> APIClient:
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Ольга", "lastName": "Петрова"},
        format="json",
    )
    access = identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def auth_client() -> APIClient:
    return _auth("reviser@example.com")


def _draft(client: APIClient, competition_id: str) -> str:
    return str(client.post("/api/v1/applications", {"competitionId": competition_id}, format="json").data["data"]["id"])


def _place(application_id: str, *, status: str = "SUBMITTED") -> None:
    """Move the order out of DRAFT without replaying the whole submit flow.

    The submit use case has its own tests; what matters here is only that the order is
    in a state the organizer has seen, which is exactly what the journal keys off.
    """
    ApplicationModel.objects.filter(pk=application_id).update(status=status, submitted_at=timezone.now())


def _age_journal(*, minutes: int) -> None:
    """Back-date every pending journal row so the sweep's quiet period has elapsed."""
    ApplicationRevisionModel.objects.filter(notified_at__isnull=True).update(created_at=timezone.now() - timedelta(minutes=minutes))


def test_editing_a_draft_is_not_journalled(auth_client: APIClient) -> None:
    application_id = _draft(auth_client, _seed_open_competition())

    auth_client.post(f"/api/v1/applications/{application_id}/submissions")

    assert ApplicationRevisionModel.objects.count() == 0


@pytest.mark.parametrize("status", ["SUBMITTED", "WAITING_PAYMENT", "PAID"])
def test_every_order_the_organizer_has_seen_is_journalled(auth_client: APIClient, status: str) -> None:
    """Including PAID — the case a status allowlist used to miss.

    An order paid early sits in PAID while registration is still open, and its
    backing track may still be swapped right up to the music deadline. That is the
    change the sound desk most needs to hear about, and it used to go unreported.
    """
    application_id = _draft(auth_client, _seed_open_competition())
    _place(application_id)
    # The performance has to exist before the order settles: an order's composition
    # freezes past SUBMITTED, so this is also the only order these statuses can have.
    submission_id = auth_client.post(f"/api/v1/applications/{application_id}/submissions").data["data"]["submissions"][0]["submissionId"]
    _place(application_id, status=status)

    auth_client.post(
        f"/api/v1/submissions/{submission_id}/teachers",
        {"firstName": "Мария", "lastName": "Иванова", "role": "TEACHER"},
        format="json",
    )

    assert ApplicationRevisionModel.objects.filter(change__startswith="Добавлен педагог").count() == 1


def test_editing_a_placed_order_is_journalled(auth_client: APIClient) -> None:
    application_id = _draft(auth_client, _seed_open_competition())
    _place(application_id)

    auth_client.post(f"/api/v1/applications/{application_id}/submissions")

    rows = list(ApplicationRevisionModel.objects.values_list("change", "notified_at"))
    assert rows == [("Добавлено новое выступление", None)]


def test_one_letter_carries_the_whole_editing_session(auth_client: APIClient) -> None:
    application_id = _draft(auth_client, _seed_open_competition())
    _place(application_id)
    submission_id = auth_client.post(f"/api/v1/applications/{application_id}/submissions").data["data"]["submissions"][0]["submissionId"]
    auth_client.post(
        f"/api/v1/submissions/{submission_id}/teachers",
        {"firstName": "Мария", "lastName": "Иванова", "role": "TEACHER"},
        format="json",
    )
    _age_journal(minutes=30)
    mail.outbox.clear()

    assert notify_application_revisions() == 1

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [_ORGANIZER_EMAIL]
    assert application_id[:8].upper() in message.subject
    assert "Добавлено новое выступление" in message.body
    assert "Добавлен педагог: Иванова Мария" in message.body
    assert "Весенний фестиваль" in message.body
    assert "Петрова Ольга" in message.body


def test_a_reported_edit_is_never_reported_again(auth_client: APIClient) -> None:
    application_id = _draft(auth_client, _seed_open_competition())
    _place(application_id)
    auth_client.post(f"/api/v1/applications/{application_id}/submissions")
    _age_journal(minutes=30)
    notify_application_revisions()
    mail.outbox.clear()

    assert notify_application_revisions() == 0

    assert mail.outbox == []
    assert ApplicationRevisionModel.objects.filter(notified_at__isnull=True).count() == 0


def test_an_order_still_being_edited_waits_for_a_later_sweep(auth_client: APIClient) -> None:
    application_id = _draft(auth_client, _seed_open_competition())
    _place(application_id)
    auth_client.post(f"/api/v1/applications/{application_id}/submissions")
    mail.outbox.clear()

    # No back-dating: the edit was made a moment ago, so the applicant may well still
    # be typing. Nothing goes out yet, and nothing is marked as reported either.
    assert notify_application_revisions() == 0

    assert mail.outbox == []
    assert ApplicationRevisionModel.objects.filter(notified_at__isnull=True).count() == 1
