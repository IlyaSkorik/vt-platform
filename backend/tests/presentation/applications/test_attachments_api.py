"""Integration tests for the Submission attachment (upload) REST API v1.

Exercises the multipart upload edge end to end against real PostgreSQL and real
file storage: a submission is created inside an application, then a file is uploaded,
validated against the competition upload policy, stored and attached.
"""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.base import uuid7
from apps.identity.presentation.api.v1.auth import composition as identity_composition

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


def _seed_open_competition() -> str:
    from apps.competitions.infrastructure.models import CompetitionModel

    competition = CompetitionModel.objects.create(organizer_id=uuid7(), status="REGISTRATION_OPEN", title="Spring", season="2025/2026")
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
    assert attachments[0]["fileReference"].startswith("applications/attachments/")


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
