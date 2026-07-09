"""Integration tests for the Participants REST API v1.

Driven through DRF's ``APIClient`` against real PostgreSQL — the full edge is
exercised end to end (serializer → command → handler → repository → response), with
authentication established by a real JWT issued from the Identity login endpoint
(ARCH-001 §28.2). The repointing to PostgreSQL is done by
``tests/presentation/conftest.py``.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.participants.infrastructure.repositories import DjangoParticipantRepository
from apps.participants.infrastructure.system import SystemClock

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_client(client: APIClient) -> APIClient:
    """An APIClient carrying a valid access token from a freshly-registered account."""
    client.post(
        "/api/v1/auth/registration",
        {
            "email": "guardian@example.com",
            "password": _PASSWORD,
            "firstName": "Olga",
            "lastName": "Petrova",
        },
        format="json",
    )
    login = client.post(
        "/api/v1/auth/sessions",
        {"email": "guardian@example.com", "password": _PASSWORD},
        format="json",
    )
    access = login.data["data"]["accessToken"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def _create(client: APIClient, *, alias: str = "Falcon-99", **overrides: Any) -> Any:
    body: dict[str, Any] = {
        "firstName": "Ivan",
        "lastName": "Petrov",
        "dateOfBirth": "2015-03-04",
        "displayAlias": alias,
    }
    body.update(overrides)
    return client.post("/api/v1/participants", body, format="json")


# ---------------------------------------------------------------------------
# Creation & retrieval
# ---------------------------------------------------------------------------


def test_create_returns_resource_envelope(auth_client: APIClient) -> None:
    response = _create(auth_client, middleName="Sergeevich")
    assert response.status_code == 201
    data = response.data["data"]
    assert data["type"] == "participant"
    assert data["displayAlias"] == "Falcon-99"
    assert data["displayName"] == "Ivan Sergeevich Petrov"
    assert data["status"] == "created"
    assert response["Location"].startswith("/api/v1/participants/")
    assert response.data["meta"]["requestId"]


def test_retrieve_returns_participant(auth_client: APIClient) -> None:
    created = _create(auth_client)
    participant_id = created.data["data"]["id"]
    response = auth_client.get(f"/api/v1/participants/{participant_id}")
    assert response.status_code == 200
    assert response.data["data"]["id"] == participant_id


def test_retrieve_missing_is_not_found(auth_client: APIClient) -> None:
    response = auth_client.get("/api/v1/participants/019f0000-0000-7000-8000-000000000000")
    assert response.status_code == 404
    assert response["Content-Type"] == "application/problem+json"


def test_create_malformed_is_bad_request(auth_client: APIClient) -> None:
    response = auth_client.post("/api/v1/participants", {"firstName": "Ivan"}, format="json")
    assert response.status_code == 400
    assert response.data["errors"]


def test_create_duplicate_alias_is_conflict(auth_client: APIClient) -> None:
    _create(auth_client, alias="Falcon-99")
    response = _create(auth_client, alias="Falcon-99")
    assert response.status_code == 409


def test_create_identity_leaking_alias_is_unprocessable(auth_client: APIClient) -> None:
    response = _create(auth_client, alias="Petrov art")
    assert response.status_code == 422


def test_requires_authentication(client: APIClient) -> None:
    assert _create(client).status_code == 401


# ---------------------------------------------------------------------------
# Guardian links & lifecycle
# ---------------------------------------------------------------------------


def test_propose_and_verify_guardian_link(auth_client: APIClient) -> None:
    participant_id = _create(auth_client).data["data"]["id"]
    guardian_id = "019f0000-0000-7000-8000-0000000000aa"
    propose = auth_client.post(
        f"/api/v1/participants/{participant_id}/guardian-links",
        {"guardianId": guardian_id, "relationshipType": "mother"},
        format="json",
    )
    assert propose.status_code == 201
    assert propose.data["data"]["guardianLinks"][0]["status"] == "proposed"

    verify = auth_client.post(f"/api/v1/participants/{participant_id}/guardian-links/{guardian_id}/verification")
    assert verify.status_code == 200
    assert verify.data["data"]["guardianLinks"][0]["status"] == "active"


def test_propose_guardian_link_malformed_is_bad_request(auth_client: APIClient) -> None:
    participant_id = _create(auth_client).data["data"]["id"]
    response = auth_client.post(
        f"/api/v1/participants/{participant_id}/guardian-links",
        {"guardianId": "not-a-uuid"},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["errors"]


def test_verify_unlinked_guardian_is_conflict(auth_client: APIClient) -> None:
    participant_id = _create(auth_client).data["data"]["id"]
    guardian_id = "019f0000-0000-7000-8000-0000000000cc"
    response = auth_client.post(f"/api/v1/participants/{participant_id}/guardian-links/{guardian_id}/verification")
    assert response.status_code == 409
    assert response["Content-Type"] == "application/problem+json"


def test_client_request_id_is_echoed(auth_client: APIClient) -> None:
    response = auth_client.post(
        "/api/v1/participants",
        {
            "firstName": "Ivan",
            "lastName": "Petrov",
            "dateOfBirth": "2015-03-04",
            "displayAlias": "Falcon-99",
        },
        format="json",
        HTTP_X_REQUEST_ID="corr-123",
    )
    assert response.status_code == 201
    assert response.data["meta"]["requestId"] == "corr-123"
    assert response["X-Request-ID"] == "corr-123"


def test_propose_guardian_link_on_missing_participant(auth_client: APIClient) -> None:
    response = auth_client.post(
        "/api/v1/participants/019f0000-0000-7000-8000-000000000000/guardian-links",
        {"guardianId": "019f0000-0000-7000-8000-0000000000aa", "relationshipType": "mother"},
        format="json",
    )
    assert response.status_code == 404


def test_verify_participant_and_wrong_state_conflict(auth_client: APIClient) -> None:
    participant_id = _create(auth_client).data["data"]["id"]
    first = auth_client.post(f"/api/v1/participants/{participant_id}/verification")
    assert first.status_code == 200
    assert first.data["data"]["status"] == "verified"
    second = auth_client.post(f"/api/v1/participants/{participant_id}/verification")
    assert second.status_code == 409


def test_activation_blocked_without_consent(auth_client: APIClient) -> None:
    participant_id = _create(auth_client).data["data"]["id"]
    auth_client.post(f"/api/v1/participants/{participant_id}/verification")
    response = auth_client.post(f"/api/v1/participants/{participant_id}/activation")
    assert response.status_code == 422
    assert "PRT-001" in response.data["code"]


def test_full_activation_flow(auth_client: APIClient) -> None:
    from apps.participants.application.commands import RecordConsentCommand
    from apps.participants.application.handlers import RecordConsentHandler
    from apps.participants.domain.value_objects import _generate_uuid7

    participant_id = _create(auth_client).data["data"]["id"]
    guardian_id = "019f0000-0000-7000-8000-0000000000bb"
    auth_client.post(
        f"/api/v1/participants/{participant_id}/guardian-links",
        {"guardianId": guardian_id, "relationshipType": "mother"},
        format="json",
    )
    auth_client.post(f"/api/v1/participants/{participant_id}/guardian-links/{guardian_id}/verification")
    auth_client.post(f"/api/v1/participants/{participant_id}/verification")
    # Consent arrives from the Identity context (ConsentGranted); record it via the
    # use case, then activation is permitted through the API (PRT-001).
    RecordConsentHandler(participants=DjangoParticipantRepository(), clock=SystemClock()).handle(
        RecordConsentCommand(
            participant_id=participant_id,
            consent_id=str(_generate_uuid7()),
            consent_version="2026-01",
        )
    )
    response = auth_client.post(f"/api/v1/participants/{participant_id}/activation")
    assert response.status_code == 200
    assert response.data["data"]["status"] == "active"
    assert response.data["data"]["consentRecorded"] is True
