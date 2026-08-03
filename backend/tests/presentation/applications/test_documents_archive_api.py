"""The organizer's paperwork archive: receipts and benefit certificates as one ZIP.

Deliberately separate from the programme's backing-track archive — this is what
accounting reconciles payments and benefit claims from, and it must not require
downloading a festival's audio to read four PDFs.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import UTC, datetime
from typing import Any

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.applications.domain.entities import Application
from apps.applications.domain.value_objects import ApplicationId, CompetitionId, FileReference, UserId
from apps.applications.infrastructure.mappers.application_mapper import ApplicationMapper
from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.base import uuid7
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_ARCHIVE = "/api/v1/staff/applications/documents.zip"
NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def _authenticated(client: APIClient, email: str) -> str:
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
    access = _authenticated(client, "organizer@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"])))  # type: ignore[arg-type]
    return client


@pytest.fixture
def outsider_client() -> APIClient:
    client = APIClient()
    _authenticated(client, "participant@example.com")
    return client


def _festival() -> uuid.UUID:
    """A competition run by the platform's own organization — the staff caller's.

    The archive is scoped to the caller's organization, so a competition that
    belongs to nobody is (rightly) invisible; these tests want the one the
    organizer actually runs.
    """
    organization_id = OrganizationModel.objects.filter(deleted_at__isnull=True).order_by("created_at").values_list("id", flat=True).first()
    # The organizer fixture provisions one; without it the archive would be empty and
    # every assertion below would pass for the wrong reason.
    assert organization_id is not None, "expected a provisioned organization"
    competition = CompetitionModel.objects.create(
        organizer_id=organization_id,
        status="PUBLISHED",
        title="Фестиваль",
        season="2025/2026",
    )
    return competition.id


def _stored(name: str, content: bytes) -> str:
    return default_storage.save(f"uploads/{uuid.uuid4()}-{name}", ContentFile(content))


def _receipts_json(references: tuple[str, ...]) -> list[dict[str, Any]]:
    """The receipts exactly as the aggregate persists them.

    Built through the real aggregate and mapper rather than hand-written: a receipt
    is stored under ``file_reference`` while an attachment uses ``file``, and a
    fixture that guessed once already made a broken archive look tested.
    """
    application, _ = Application.create(
        application_id=ApplicationId.generate(),
        competition_id=CompetitionId.from_uuid(uuid7()),
        applicant_id=UserId.from_uuid(uuid7()),
        now=NOW,
    )
    for reference in references:
        application.upload_payment_receipt(file=FileReference(reference), now=NOW)
    receipts: list[dict[str, Any]] = ApplicationMapper.to_model(application).payment_receipts
    return receipts


def _order(
    *,
    competition_id: uuid.UUID,
    performer: str,
    receipts: tuple[str, ...] = (),
    benefits: tuple[tuple[str, str], ...] = (),
) -> ApplicationModel:
    """One order with a lead performer, any receipts it paid with, and any benefit files."""
    submission = SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        attachments=[{"id": str(uuid.uuid4()), "type": "BENEFIT", "file": reference, "caption": caption} for caption, reference in benefits],
    )
    return ApplicationModel.objects.create(
        competition_id=competition_id,
        applicant_id=submission.applicant_id,
        status="SUBMITTED",
        submission_refs=[{"submission_id": str(submission.id), "participant_display_name": performer}],
        payment_receipts=_receipts_json(receipts),
    )


def _archive(response: Any) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))


class TestDocumentsArchive:
    def test_a_receipt_and_its_benefit_certificate_land_in_one_folder(self, staff_client: APIClient) -> None:
        competition_id = _festival()
        order = _order(
            competition_id=competition_id,
            performer="Иванова Анна",
            receipts=(_stored("receipt.pdf", b"receipt"),),
            benefits=(("Справка о многодетной семье", _stored("benefit.pdf", b"benefit")),),
        )
        short = str(order.id).split("-")[0]

        response = staff_client.get(f"{_ARCHIVE}?competitionId={competition_id}")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        with _archive(response) as archive:
            assert sorted(archive.namelist()) == [
                f"Иванова Анна — {short}/Квитанция.pdf",
                f"Иванова Анна — {short}/Справка о многодетной семье.pdf",
            ]
            assert archive.read(f"Иванова Анна — {short}/Квитанция.pdf") == b"receipt"

    def test_an_order_paid_in_several_transfers_keeps_every_slip(self, staff_client: APIClient) -> None:
        # A group fee split between a school and a parent arrives as two payments.
        # Keeping only one of the slips would leave the folder short of the sum.
        competition_id = _festival()
        order = _order(
            competition_id=competition_id,
            performer="Иванова Анна",
            receipts=(_stored("part-one.pdf", b"first"), _stored("part-two.jpg", b"second")),
        )
        short = str(order.id).split("-")[0]

        response = staff_client.get(f"{_ARCHIVE}?competitionId={competition_id}")
        with _archive(response) as archive:
            assert sorted(archive.namelist()) == [
                f"Иванова Анна — {short}/Квитанция 1.pdf",
                f"Иванова Анна — {short}/Квитанция 2.jpg",
            ]
            assert archive.read(f"Иванова Анна — {short}/Квитанция 2.jpg") == b"second"

    def test_an_order_with_no_paperwork_is_listed_rather_than_silently_absent(self, staff_client: APIClient) -> None:
        competition_id = _festival()
        _order(competition_id=competition_id, performer="Петров Пётр")

        response = staff_client.get(f"{_ARCHIVE}?competitionId={competition_id}")
        with _archive(response) as archive:
            assert archive.namelist() == ["ПРОЧТИ.txt"]
            assert "Без квитанции: Петров Пётр" in archive.read("ПРОЧТИ.txt").decode()

    def test_a_benefit_without_a_receipt_is_still_flagged(self, staff_client: APIClient) -> None:
        # The case worth chasing: a claim for a reduced fee with no proof that the
        # reduced fee was ever paid. Counting documents would call this folder done.
        competition_id = _festival()
        _order(
            competition_id=competition_id,
            performer="Петров Пётр",
            benefits=(("Справка о льготе", _stored("benefit.pdf", b"benefit")),),
        )

        response = staff_client.get(f"{_ARCHIVE}?competitionId={competition_id}")
        with _archive(response) as archive:
            assert any(name.endswith("Справка о льготе.pdf") for name in archive.namelist())
            assert "Без квитанции: Петров Пётр" in archive.read("ПРОЧТИ.txt").decode()

    def test_an_order_that_paid_is_not_flagged(self, staff_client: APIClient) -> None:
        competition_id = _festival()
        _order(competition_id=competition_id, performer="Иванова Анна", receipts=(_stored("r.pdf", b"r"),))

        response = staff_client.get(f"{_ARCHIVE}?competitionId={competition_id}")
        with _archive(response) as archive:
            assert "ПРОЧТИ.txt" not in archive.namelist()

    def test_the_archive_is_scoped_to_the_competition_asked_for(self, staff_client: APIClient) -> None:
        wanted, other = _festival(), _festival()
        _order(competition_id=wanted, performer="Иванова Анна", receipts=(_stored("a.pdf", b"a"),))
        _order(competition_id=other, performer="Сидоров Иван", receipts=(_stored("b.pdf", b"b"),))

        response = staff_client.get(f"{_ARCHIVE}?competitionId={wanted}")
        with _archive(response) as archive:
            assert all("Сидоров" not in name for name in archive.namelist())
            assert any("Иванова Анна" in name for name in archive.namelist())

    def test_music_never_enters_the_paperwork_archive(self, staff_client: APIClient) -> None:
        competition_id = _festival()
        order = _order(competition_id=competition_id, performer="Иванова Анна", receipts=(_stored("r.pdf", b"r"),))
        submission_id = order.submission_refs[0]["submission_id"]
        submission = SubmissionModel.objects.get(id=submission_id)
        submission.attachments = [{"id": str(uuid.uuid4()), "type": "MUSIC", "file": _stored("t.mp3", b"track"), "caption": None}]
        submission.save(update_fields=["attachments"])

        response = staff_client.get(f"{_ARCHIVE}?competitionId={competition_id}")
        with _archive(response) as archive:
            assert all(not name.endswith(".mp3") for name in archive.namelist())

    def test_a_non_staff_caller_is_refused(self, outsider_client: APIClient) -> None:
        assert outsider_client.get(_ARCHIVE).status_code == 403
