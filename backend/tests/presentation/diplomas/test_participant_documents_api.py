"""Integration tests for the participant's documents endpoint ("Мои документы").

Driven through DRF's ``APIClient`` as an authenticated applicant. Covers what the
cabinet must and must not show: a thank-you letter appears the moment it is
generated (no organizer step), a diploma only once its official PDF exists, and one
participant never sees another's documents.

Also the one download that is not a single file: an entry's individual diplomas as
one ZIP, which is how an ensemble of twelve is actually handed out.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import quote

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.diplomas.infrastructure.models import DiplomaModel, IssuedDocumentModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_django.fixtures import SettingsWrapper

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


def _thank_you(submission: SubmissionModel, *, published: bool = True, recipient: str = "Петрова Ольга") -> IssuedDocumentModel:
    return IssuedDocumentModel.objects.create(
        document_type="THANK_YOU",
        competition_id=submission.competition_id,
        submission_id=submission.id,
        template_id=uuid.uuid4(),
        recipient=recipient,
        snapshot=_SNAPSHOT,
        pdf_path=f"/media/diplomas/documents/x/thank_you/{recipient}.pdf",
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

    def test_a_letter_per_teacher_is_listed_separately(self) -> None:
        client, applicant = _applicant("twoteachers@example.com")
        submission = _submission(applicant)
        _thank_you(submission, recipient="Петрова Ольга")
        _thank_you(submission, recipient="Сидоров Иван")

        response = client.get("/api/v1/me/documents")

        rows = response.data["data"]
        # Two addressed letters for one entry, told apart by their recipient.
        assert [row["documentType"] for row in rows] == ["THANK_YOU", "THANK_YOU"]
        assert {row["recipient"] for row in rows} == {"Петрова Ольга", "Сидоров Иван"}
        assert len({row["fileUrl"] for row in rows}) == 2

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


def _individual(submission: SubmissionModel, *, recipient: str, number: str) -> DiplomaModel:
    """One member's own diploma, issued and downloadable."""
    key = f"diplomas/official/x/{number}.pdf"
    default_storage.save(key, ContentFile(b"%PDF-1.4 individual"))
    return DiplomaModel.objects.create(
        number=number,
        verification_token=uuid.uuid4().hex,
        document_type="INDIVIDUAL_DIPLOMA",
        recipient=recipient,
        competition_id=submission.competition_id,
        submission_id=submission.id,
        template_id=uuid.uuid4(),
        status="ISSUED",
        snapshot={**_SNAPSHOT, "member": {"full_name": recipient}},
        official_pdf_path=f"/media/{key}",
        issued_at=_NOW,
    )


class TestIndividualDiplomaArchive:
    """Twelve members mean twelve diplomas, and one download."""

    @pytest.fixture(autouse=True)
    def _media_root(self, settings: SettingsWrapper, tmp_path: Path) -> None:
        settings.MEDIA_ROOT = str(tmp_path)

    def test_bundles_one_entry_into_a_named_archive(self) -> None:
        client, applicant = _applicant("bundle@example.com")
        submission = _submission(applicant)
        _individual(submission, recipient="Петров Пётр", number="VT-2026-000002")
        _individual(submission, recipient="Иванова Мария", number="VT-2026-000003")

        response = client.get(f"/api/v1/me/documents/archive?submissionId={submission.id}")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        # The festival's real name, RFC 5987-encoded for the browser.
        assert quote("Дипломы участников — Восходящие таланты.zip") in response["Content-Disposition"]
        with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
            names = archive.namelist()
        # Named after the person the sheet is handed to, numbered in listing order —
        # alphabetical here, because one publication issues them in the same instant.
        assert names == ["01 — Иванова Мария — VT-2026-000003.pdf", "02 — Петров Пётр — VT-2026-000002.pdf"]

    def test_carries_only_the_named_entry(self) -> None:
        client, applicant = _applicant("oneentry@example.com")
        wanted = _submission(applicant)
        other = _submission(applicant)
        _individual(wanted, recipient="Иванова Мария", number="VT-2026-000004")
        _individual(other, recipient="Сидоров Иван", number="VT-2026-000005")

        response = client.get(f"/api/v1/me/documents/archive?submissionId={wanted.id}")

        with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
            names = archive.namelist()
        # Two festivals' worth of diplomas in one folder is not a bundle anybody wants.
        assert names == ["01 — Иванова Мария — VT-2026-000004.pdf"]

    def test_the_collective_diploma_is_not_in_it(self) -> None:
        client, applicant = _applicant("collective@example.com")
        submission = _submission(applicant)
        _diploma(submission, official=True)
        _individual(submission, recipient="Иванова Мария", number="VT-2026-000006")

        response = client.get(f"/api/v1/me/documents/archive?submissionId={submission.id}")

        with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
            names = archive.namelist()
        # The ensemble's own sheet is one download of its own, right above the bundle.
        assert names == ["01 — Иванова Мария — VT-2026-000006.pdf"]

    def test_another_participants_entry_is_not_found(self) -> None:
        client, _mine = _applicant("notmine@example.com")
        _, theirs = _applicant("hers@example.com")
        submission = _submission(theirs)
        _individual(submission, recipient="Иванова Мария", number="VT-2026-000007")

        response = client.get(f"/api/v1/me/documents/archive?submissionId={submission.id}")

        # The id in the query is not a permission: the bundle is filtered out of the
        # caller's own documents, so somebody else's entry simply matches nothing.
        assert response.status_code == 404

    def test_an_entry_without_individual_diplomas_is_not_found(self) -> None:
        client, applicant = _applicant("nobundle@example.com")
        submission = _submission(applicant)
        _diploma(submission, official=True)

        response = client.get(f"/api/v1/me/documents/archive?submissionId={submission.id}")

        assert response.status_code == 404

    def test_a_malformed_entry_id_is_rejected(self) -> None:
        client, _applicant_id = _applicant("badid@example.com")

        response = client.get("/api/v1/me/documents/archive?submissionId=not-a-uuid")

        assert response.status_code == 400

    def test_anonymous_access_is_refused(self) -> None:
        response = APIClient().get(f"/api/v1/me/documents/archive?submissionId={uuid.uuid4()}")

        assert response.status_code == 401
