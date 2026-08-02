"""Integration tests for the Submission attachment (upload) REST API v1.

Exercises the multipart upload edge end to end against real PostgreSQL and real
file storage: a submission is created inside an application, then a file is uploaded,
validated against the competition upload policy, stored and attached.
"""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.base import uuid7
from apps.identity.presentation.api.v1.auth import composition as identity_composition

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


def _seed_open_competition() -> str:
    from datetime import UTC, datetime

    from apps.competitions.infrastructure.models import CategoryModel, CompetitionModel

    competition = CompetitionModel.objects.create(organizer_id=uuid7(), status="PUBLISHED", title="Spring", season="2025/2026")
    # An open nomination window is what admits applications (registration is per nomination).
    CategoryModel.objects.create(
        competition=competition,
        name="Vocal",
        registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
        registration_closes_at=datetime(2100, 1, 1, tzinfo=UTC),
    )
    return str(competition.id)


def _auth(client: APIClient, *, email: str) -> APIClient:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Olga", "lastName": "Petrova"},
        format="json",
    )
    # Mint the session token directly: the login gate refuses unverified accounts,
    # and this BC test only needs an authenticated caller, not the verify flow.
    access = identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def auth_client() -> APIClient:
    return _auth(APIClient(), email="uploader@example.com")


def _submission_in_application(client: APIClient) -> str:
    competition_id = _seed_open_competition()
    app_id = client.post("/api/v1/applications", {"competitionId": competition_id}, format="json").data["data"]["id"]
    added = client.post(f"/api/v1/applications/{app_id}/submissions")
    return str(added.data["data"]["submissions"][0]["submissionId"])


def test_upload_stores_and_attaches(auth_client: APIClient) -> None:
    submission_id = _submission_in_application(auth_client)
    upload = SimpleUploadedFile("track.mp3", b"ID3 fake audio bytes", content_type="audio/mpeg")
    response = auth_client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        {"file": upload, "attachmentType": "MUSIC", "caption": "Backing track"},
        format="multipart",
    )
    assert response.status_code == 201, response.data
    attachments = response.data["data"]["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["type"] == "MUSIC"
    # A URL the browser can open, not the bare storage key: the aggregate keeps an opaque
    # key, and the edge resolves it against whichever storage is configured. Before object
    # storage this worked only because the client guessed a `/media/` prefix.
    assert attachments[0]["fileReference"].startswith("/media/applications/attachments/")


def _force_status(submission_id: str, status: str) -> None:
    """Put a submission into a later lifecycle state, the way the organizer would."""
    from apps.applications.infrastructure.models.submission import SubmissionModel

    SubmissionModel.objects.filter(id=submission_id).update(status=status)


def test_several_phonograms_may_be_attached_to_one_submission(auth_client: APIClient) -> None:
    """One act, several tracks: an intro and the number itself are two files."""
    submission_id = _submission_in_application(auth_client)
    for name in ("intro.mp3", "main.mp3"):
        response = auth_client.post(
            f"/api/v1/submissions/{submission_id}/attachments",
            {"file": SimpleUploadedFile(name, b"ID3 fake audio bytes", content_type="audio/mpeg"), "attachmentType": "MUSIC"},
            format="multipart",
        )
        assert response.status_code == 201, response.data
    attachments = response.data["data"]["attachments"]
    assert [PurePosixPath(a["fileReference"]).name for a in attachments] == ["intro.mp3", "main.mp3"]


def test_a_phonogram_may_still_be_uploaded_after_the_entry_is_accepted(auth_client: APIClient) -> None:
    """The state a running order is built from is the state a track is wanted in.

    An entry only reaches a programme once it is ``ACCEPTED``; if the content freeze
    also froze the phonogram, the organizer's archive could never be anything but empty.
    """
    submission_id = _submission_in_application(auth_client)
    _force_status(submission_id, "ACCEPTED")
    response = auth_client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        {"file": SimpleUploadedFile("late.mp3", b"ID3 fake audio bytes", content_type="audio/mpeg"), "attachmentType": "MUSIC"},
        format="multipart",
    )
    assert response.status_code == 201, response.data
    assert response.data["data"]["attachments"][0]["type"] == "MUSIC"


def test_paperwork_stays_frozen_once_the_entry_is_accepted(auth_client: APIClient) -> None:
    """Only the backing track outlives the freeze — a document is a claim about the entry."""
    submission_id = _submission_in_application(auth_client)
    _force_status(submission_id, "ACCEPTED")
    response = auth_client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        {"file": SimpleUploadedFile("spravka.pdf", b"%PDF-1.4", content_type="application/pdf"), "attachmentType": "DOCUMENT"},
        format="multipart",
    )
    assert response.status_code == 409
    assert response["Content-Type"] == "application/problem+json"


def test_upload_rejects_unsupported_type(auth_client: APIClient) -> None:
    submission_id = _submission_in_application(auth_client)
    upload = SimpleUploadedFile("malware.exe", b"MZ...", content_type="application/octet-stream")
    response = auth_client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        {"file": upload, "attachmentType": "MUSIC"},
        format="multipart",
    )
    assert response.status_code == 415
    assert response["Content-Type"] == "application/problem+json"


def test_upload_requires_authentication() -> None:
    upload = SimpleUploadedFile("track.mp3", b"bytes", content_type="audio/mpeg")
    response = APIClient().post(f"/api/v1/submissions/{uuid7()}/attachments", {"file": upload, "attachmentType": "MUSIC"}, format="multipart")
    assert response.status_code == 401
