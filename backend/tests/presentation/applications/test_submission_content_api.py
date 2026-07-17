"""Integration tests for the Submission content REST edge (build a performance).

Proves the Registration Wizard's core backend path: create an application, add a
submission, set its performance, add a participant/teacher, and read it back - all
end to end against real PostgreSQL with JWT auth.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.base import uuid7
from apps.identity.presentation.api.v1.auth import composition as identity_composition

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


def _seed_open_competition() -> str:
    from apps.competitions.infrastructure.models import CompetitionModel

    competition = CompetitionModel.objects.create(organizer_id=uuid7(), status="REGISTRATION_OPEN", title="Spring", season="2025/2026")
    return str(competition.id)


@pytest.fixture
def auth_client() -> APIClient:
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "builder@example.com", "password": _PASSWORD, "firstName": "Olga", "lastName": "Petrova"},
        format="json",
    )
    # Mint the session token directly: the login gate refuses unverified accounts,
    # and this BC test only needs an authenticated caller, not the verify flow.
    access = identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def _submission(client: APIClient) -> str:
    app_id = client.post("/api/v1/applications", {"competitionId": _seed_open_competition()}, format="json").data["data"]["id"]
    added = client.post(f"/api/v1/applications/{app_id}/submissions")
    return str(added.data["data"]["submissions"][0]["submissionId"])


def _performance_body() -> dict[str, Any]:
    return {
        "title": "Swan Lake",
        "durationSeconds": 210,
        "nominationId": str(uuid7()),
        "disciplineId": str(uuid7()),
        "ageCategoryId": str(uuid7()),
        "participantGroupId": str(uuid7()),
        "participationFormatId": str(uuid7()),
    }


def test_build_performance_and_participant(auth_client: APIClient) -> None:
    submission_id = _submission(auth_client)

    perf = auth_client.put(f"/api/v1/submissions/{submission_id}/performance", _performance_body(), format="json")
    assert perf.status_code == 200, perf.data
    assert perf.data["data"]["performance"]["title"] == "Swan Lake"

    participant = auth_client.post(
        f"/api/v1/submissions/{submission_id}/participants",
        {"firstName": "Anna", "lastName": "Ivanova", "birthDate": "2014-05-01", "gender": "FEMALE"},
        format="json",
    )
    assert participant.status_code == 201
    assert len(participant.data["data"]["participants"]) == 1

    teacher = auth_client.post(
        f"/api/v1/submissions/{submission_id}/teachers",
        {"firstName": "Olga", "lastName": "Petrova", "role": "Choreographer"},
        format="json",
    )
    assert teacher.status_code == 201

    fetched = auth_client.get(f"/api/v1/submissions/{submission_id}")
    assert fetched.status_code == 200
    data = fetched.data["data"]
    assert data["performance"]["durationSeconds"] == 210
    assert len(data["participants"]) == 1
    assert len(data["teachers"]) == 1


def test_set_performance_rejects_malformed_id(auth_client: APIClient) -> None:
    submission_id = _submission(auth_client)
    body = _performance_body()
    body["nominationId"] = "not-a-uuid"
    response = auth_client.put(f"/api/v1/submissions/{submission_id}/performance", body, format="json")
    assert response.status_code == 400


def test_get_submission_requires_owner(auth_client: APIClient) -> None:
    submission_id = _submission(auth_client)
    other = APIClient()
    registration = other.post(
        "/api/v1/auth/registration",
        {"email": "intruder@example.com", "password": _PASSWORD, "firstName": "X", "lastName": "Y"},
        format="json",
    )
    access = identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token
    other.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert other.get(f"/api/v1/submissions/{submission_id}").status_code in (403, 404)
