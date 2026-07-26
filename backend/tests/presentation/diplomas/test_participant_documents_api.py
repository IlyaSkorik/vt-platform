"""Integration tests for the participant's documents endpoint ("Мои документы").

Driven through DRF's ``APIClient`` as an authenticated applicant. Covers what the
cabinet must and must not show: a thank-you letter appears the moment it is
generated (no organizer step), a diploma only once its official PDF exists, and one
participant never sees another's documents.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.diplomas.infrastructure.models import DiplomaModel, IssuedDocumentModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition

pytestmark = pytest.mark.django_db

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
_PASSWORD = "V3ry$ecurePass!"


def _applicant(email: str) -> tuple[APIClient, uuid.UUID]:
    """A registered applicant and an APIClient authenticated as them.

    A real user (rather than a hand-rolled token) because the cabinet scopes on the
    authenticated caller's own id — the whole point of the endpoint — so the id has
    to be one the auth layer actually resolves.
    """
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Ivan", "lastName": "Ivanov"},
        format="json",
    )
    user_id = registration.data["data"]["id"]
    # Mint the session token directly: the login gate refuses unverified accounts,
    # and these tests need an authenticated caller, not the verify flow.
    access = identity_composition.build_token_service().issue(subject=user_id).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client, uuid.UUID(str(user_id))


def _submission(applicant_id: uuid.UUID) -> SubmissionModel:
    return SubmissionModel.objects.create(
        competition_id=uuid.uuid4(),
        applicant_id=applicant_id,
        status="SUBMITTED",
        participants=[{"display_name": "Иванов Иван", "member_count": 1}],
        teachers=[],
        performance={"title": "Этюд"},
    )


_SNAPSHOT = {
    "participant": {"display_name": "Иванов Иван"},
    "competition": {"title": "Восходящие таланты"},
    "nomination": {"title": "Вокал"},
    "award": {"degree": "Лауреат I степени"},
}


def _thank_you(submission: SubmissionModel, *, published: bool = True) -> IssuedDocumentModel:
    return IssuedDocumentModel.objects.create(
        document_type="THANK_YOU",
        competition_id=submission.competition_id,
        submission_id=submission.id,
        template_id=uuid.uuid4(),
        snapshot=_SNAPSHOT,
        pdf_path="/media/diplomas/documents/x/thank_you/1.pdf",
        published_at=_NOW if published else None,
    )


def _diploma(submission: SubmissionModel, *, official: bool) -> DiplomaModel:
    return DiplomaModel.objects.create(
        number="VT-2026-000001",
        verification_token=uuid.uuid4().hex,
        competition_id=submission.competition_id,
        submission_id=submission.id,
        template_id=uuid.uuid4(),
        status="GENERATED",
        snapshot=_SNAPSHOT,
        print_pdf_path="/media/diplomas/print/x/VT-2026-000001.pdf",
        official_pdf_path="/media/diplomas/official/x/VT-2026-000001.pdf" if official else "",
        issued_at=_NOW if official else None,
    )


class TestThankYouVisibility:
    def test_a_generated_letter_needs_no_publication_step(self) -> None:
        client, applicant = _applicant("thanks@example.com")
        _thank_you(_submission(applicant))

        response = client.get("/api/v1/me/documents")

        assert response.status_code == 200
        rows = response.data["data"]
        assert [row["documentType"] for row in rows] == ["THANK_YOU"]
        assert rows[0]["participantName"] == "Иванов Иван"
        assert rows[0]["fileUrl"].endswith(".pdf")
        # A courtesy letter is neither numbered nor ranked.
        assert rows[0]["number"] is None
        assert rows[0]["degree"] is None

    def test_an_unpublished_document_stays_hidden(self) -> None:
        client, applicant = _applicant("unpublished@example.com")
        _thank_you(_submission(applicant), published=False)

        response = client.get("/api/v1/me/documents")

        assert response.data["data"] == []


class TestDiplomaVisibility:
    def test_the_print_copy_never_reaches_the_cabinet(self) -> None:
        client, applicant = _applicant("printonly@example.com")
        # Rendered for the organizer's printer, but not yet the participant's.
        _diploma(_submission(applicant), official=False)

        response = client.get("/api/v1/me/documents")

        assert response.data["data"] == []

    def test_the_official_diploma_is_shown_with_its_number_and_degree(self) -> None:
        client, applicant = _applicant("official@example.com")
        _diploma(_submission(applicant), official=True)

        response = client.get("/api/v1/me/documents")

        rows = response.data["data"]
        assert [row["documentType"] for row in rows] == ["DIPLOMA"]
        assert rows[0]["number"] == "VT-2026-000001"
        assert rows[0]["degree"] == "Лауреат I степени"
        assert "official" in rows[0]["fileUrl"]


class TestOrderingAndScope:
    def test_the_diploma_leads_the_courtesy_letter(self) -> None:
        client, applicant = _applicant("both@example.com")
        submission = _submission(applicant)
        _thank_you(submission)
        _diploma(submission, official=True)

        response = client.get("/api/v1/me/documents")

        assert [row["documentType"] for row in response.data["data"]] == ["DIPLOMA", "THANK_YOU"]

    def test_one_participant_cannot_see_anothers_documents(self) -> None:
        client, _mine = _applicant("mine@example.com")
        _, theirs = _applicant("theirs@example.com")
        _thank_you(_submission(theirs))

        response = client.get("/api/v1/me/documents")

        # Scoped to the caller's own applicant id, never to one from the request.
        assert response.data["data"] == []

    def test_anonymous_access_is_refused(self) -> None:
        response = APIClient().get("/api/v1/me/documents")

        assert response.status_code == 401
