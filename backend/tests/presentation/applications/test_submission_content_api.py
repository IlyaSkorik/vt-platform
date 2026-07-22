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


def _seed_open_competition() -> tuple[str, str]:
    """Seed a competition with one open nomination; return (competition_id, nomination_id)."""
    from datetime import UTC, datetime

    from apps.competitions.infrastructure.models import CategoryModel, CompetitionModel

    competition = CompetitionModel.objects.create(organizer_id=uuid7(), status="REGISTRATION_OPEN", title="Spring", season="2025/2026")
    category = CategoryModel.objects.create(
        competition=competition,
        name="Vocal",
        registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
        registration_closes_at=datetime(2100, 1, 1, tzinfo=UTC),
    )
    return str(competition.id), str(category.id)


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


def _submission(client: APIClient) -> tuple[str, str]:
    """Create an application + submission in an open nomination; return (submission_id, nomination_id)."""
    competition_id, nomination_id = _seed_open_competition()
    app_id = client.post("/api/v1/applications", {"competitionId": competition_id}, format="json").data["data"]["id"]
    added = client.post(f"/api/v1/applications/{app_id}/submissions")
    return str(added.data["data"]["submissions"][0]["submissionId"]), nomination_id


def _performance_body(nomination_id: str) -> dict[str, Any]:
    return {
        "title": "Swan Lake",
        "durationSeconds": 210,
        "nominationId": nomination_id,
        "disciplineId": str(uuid7()),
        "ageCategoryId": str(uuid7()),
        "participantGroupId": str(uuid7()),
        "participationFormatId": str(uuid7()),
    }


def test_build_performance_and_participant(auth_client: APIClient) -> None:
    submission_id, nomination_id = _submission(auth_client)

    perf = auth_client.put(f"/api/v1/submissions/{submission_id}/performance", _performance_body(nomination_id), format="json")
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
    submission_id, nomination_id = _submission(auth_client)
    body = _performance_body(nomination_id)
    body["nominationId"] = "not-a-uuid"
    response = auth_client.put(f"/api/v1/submissions/{submission_id}/performance", body, format="json")
    assert response.status_code == 400


def test_get_submission_requires_owner(auth_client: APIClient) -> None:
    submission_id, _nomination_id = _submission(auth_client)
    other = APIClient()
    registration = other.post(
        "/api/v1/auth/registration",
        {"email": "intruder@example.com", "password": _PASSWORD, "firstName": "X", "lastName": "Y"},
        format="json",
    )
    access = identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token
    other.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert other.get(f"/api/v1/submissions/{submission_id}").status_code in (403, 404)
