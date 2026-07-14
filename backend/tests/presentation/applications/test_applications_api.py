"""Integration tests for the Application (order) REST API v1.

Driven through DRF's ``APIClient`` against real PostgreSQL - the full edge end to
end (serializer -> command -> handler -> repository/ACL -> response), authenticated
with a real JWT from the Identity login endpoint. A competition open for
applications is seeded directly so the create path's Competition ACL check passes.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.base import uuid7

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


def _seed_open_competition() -> str:
    """Seed a competition that is open for applications; return its id string."""
    from apps.competitions.infrastructure.models import CompetitionModel

    competition = CompetitionModel.objects.create(
        organizer_id=uuid7(),
        status="REGISTRATION_OPEN",
        title="Spring Festival",
        season="2025/2026",
    )
    return str(competition.id)


def _auth(client: APIClient, *, email: str) -> APIClient:
    client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Olga", "lastName": "Petrova"},
        format="json",
    )
    login = client.post("/api/v1/auth/sessions", {"email": email, "password": _PASSWORD}, format="json")
    access = login.data["data"]["accessToken"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def auth_client() -> APIClient:
    return _auth(APIClient(), email="applicant@example.com")


def _create(client: APIClient, competition_id: str) -> Any:
    return client.post("/api/v1/applications", {"competitionId": competition_id}, format="json")


def test_requires_authentication() -> None:
    assert APIClient().get("/api/v1/applications").status_code == 401


def test_create_returns_resource_envelope(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    response = _create(auth_client, competition_id)
    assert response.status_code == 201, response.data
    data = response.data["data"]
    assert data["type"] == "application"
    assert data["status"] == "DRAFT"
    assert data["competitionId"] == competition_id
    assert data["totalPrice"]["totalAmount"] == "0.00"
    assert response["Location"].startswith("/api/v1/applications/")


def test_create_unknown_competition_is_404(auth_client: APIClient) -> None:
    response = _create(auth_client, str(uuid7()))
    assert response.status_code == 404
    assert response["Content-Type"] == "application/problem+json"


def test_list_and_drafts_filter(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    _create(auth_client, competition_id)
    listed = auth_client.get("/api/v1/applications")
    assert listed.status_code == 200
    assert len(listed.data["data"]) == 1
    drafts = auth_client.get("/api/v1/applications?status=DRAFT")
    assert len(drafts.data["data"]) == 1


def test_add_submission_and_retrieve(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    added = auth_client.post(f"/api/v1/applications/{app_id}/submissions")
    assert added.status_code == 201
    assert len(added.data["data"]["submissions"]) == 1
    fetched = auth_client.get(f"/api/v1/applications/{app_id}")
    assert fetched.status_code == 200
    assert len(fetched.data["data"]["submissions"]) == 1


def test_record_consents(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    response = auth_client.put(
        f"/api/v1/applications/{app_id}/consents",
        {"consents": [{"code": "personal_data", "version": "v1"}]},
        format="json",
    )
    assert response.status_code == 200
    assert [c["code"] for c in response.data["data"]["consents"]] == ["personal_data"]


def test_select_unknown_service_is_404(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    response = auth_client.post(f"/api/v1/applications/{app_id}/services", {"serviceId": str(uuid7())}, format="json")
    assert response.status_code == 404


def test_remove_submission(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    submission_id = auth_client.post(f"/api/v1/applications/{app_id}/submissions").data["data"]["submissions"][0]["submissionId"]
    removed = auth_client.delete(f"/api/v1/applications/{app_id}/submissions/{submission_id}")
    assert removed.status_code == 200
    assert removed.data["data"]["submissions"] == []


def test_cancel(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    response = auth_client.post(f"/api/v1/applications/{app_id}/cancellation")
    assert response.status_code == 200
    assert response.data["data"]["status"] == "CANCELLED"


def test_receipt_upload_on_draft_is_conflict(auth_client: APIClient) -> None:
    # End-to-end wiring of the receipt endpoint: a DRAFT order has nothing to pay
    # for, so uploading a receipt is a 409 (problem+json). The happy path is covered
    # by the handler tests, which can reach the awaiting-payment state cheaply.
    from django.core.files.uploadedfile import SimpleUploadedFile

    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    receipt = SimpleUploadedFile("receipt.pdf", b"%PDF-1.4 paid", content_type="application/pdf")
    response = auth_client.post(f"/api/v1/applications/{app_id}/receipt", {"file": receipt}, format="multipart")
    assert response.status_code == 409, response.data
    assert response["Content-Type"] == "application/problem+json"


def test_ownership_isolation() -> None:
    competition_id = _seed_open_competition()
    owner = _auth(APIClient(), email="owner-a@example.com")
    app_id = _create(owner, competition_id).data["data"]["id"]
    other = _auth(APIClient(), email="owner-b@example.com")
    assert other.get(f"/api/v1/applications/{app_id}").status_code == 403
    assert other.get("/api/v1/applications").data["data"] == []
