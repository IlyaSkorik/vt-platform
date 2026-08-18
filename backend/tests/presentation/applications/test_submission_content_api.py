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

    competition = CompetitionModel.objects.create(organizer_id=uuid7(), status="PUBLISHED", title="Spring", season="2025/2026")
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


def test_performance_comment_round_trips(auth_client: APIClient) -> None:
    """The applicant's note for the organizers is stored and read back verbatim."""
    submission_id, nomination_id = _submission(auth_client)
    body = _performance_body(nomination_id)
    body["comment"] = "  Выход с точки 3. Фонограмма начинается не с начала.  "

    saved = auth_client.put(f"/api/v1/submissions/{submission_id}/performance", body, format="json")
    assert saved.status_code == 200, saved.data
    assert saved.data["data"]["performance"]["comment"] == "Выход с точки 3. Фонограмма начинается не с начала."

    fetched = auth_client.get(f"/api/v1/submissions/{submission_id}")
    assert fetched.data["data"]["performance"]["comment"] == "Выход с точки 3. Фонограмма начинается не с начала."


def test_performance_comment_is_optional_and_defaults_to_blank(auth_client: APIClient) -> None:
    submission_id, nomination_id = _submission(auth_client)
    response = auth_client.put(f"/api/v1/submissions/{submission_id}/performance", _performance_body(nomination_id), format="json")
    assert response.status_code == 200, response.data
    assert response.data["data"]["performance"]["comment"] == ""


def test_performance_comment_can_be_cleared(auth_client: APIClient) -> None:
    submission_id, nomination_id = _submission(auth_client)
    filled = _performance_body(nomination_id) | {"comment": "нужен микрофон на стойке"}
    auth_client.put(f"/api/v1/submissions/{submission_id}/performance", filled, format="json")

    cleared = auth_client.put(f"/api/v1/submissions/{submission_id}/performance", _performance_body(nomination_id) | {"comment": ""}, format="json")
    assert cleared.status_code == 200, cleared.data
    assert cleared.data["data"]["performance"]["comment"] == ""


def test_performance_comment_over_the_limit_is_rejected(auth_client: APIClient) -> None:
    submission_id, nomination_id = _submission(auth_client)
    body = _performance_body(nomination_id) | {"comment": "я" * 1_001}
    response = auth_client.put(f"/api/v1/submissions/{submission_id}/performance", body, format="json")
    assert response.status_code == 400


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


def _collective(client: APIClient, submission_id: str, nomination_id: str) -> str:
    """Attach a collective to the submission; return its participant id."""
    client.put(f"/api/v1/submissions/{submission_id}/performance", _performance_body(nomination_id), format="json")
    added = client.post(
        f"/api/v1/submissions/{submission_id}/participants",
        {"displayName": "Ансамбль «Созвездие»", "memberCount": 3},
        format="json",
    )
    assert added.status_code == 201, added.data
    return str(added.data["data"]["participants"][0]["id"])


def test_collective_members_round_trip(auth_client: APIClient) -> None:
    """Naming the people in a collective is how the applicant asks for individual diplomas."""
    submission_id, nomination_id = _submission(auth_client)
    participant_id = _collective(auth_client, submission_id, nomination_id)

    saved = auth_client.put(
        f"/api/v1/submissions/{submission_id}/participants/{participant_id}/members",
        {"members": ["  Иванова Мария Петровна ", "", "Петров Пётр Петрович"]},
        format="json",
    )

    assert saved.status_code == 200, saved.data
    # Trimmed, blank rows dropped (the form has spare rows by design), order kept.
    assert saved.data["data"]["participants"][0]["members"] == ["Иванова Мария Петровна", "Петров Пётр Петрович"]
    fetched = auth_client.get(f"/api/v1/submissions/{submission_id}")
    assert fetched.data["data"]["participants"][0]["members"] == ["Иванова Мария Петровна", "Петров Пётр Петрович"]


def test_collective_members_are_optional_and_start_empty(auth_client: APIClient) -> None:
    submission_id, nomination_id = _submission(auth_client)
    _collective(auth_client, submission_id, nomination_id)

    fetched = auth_client.get(f"/api/v1/submissions/{submission_id}")

    # An applicant who wants only the collective's own diploma never touches the roster.
    assert fetched.data["data"]["participants"][0]["members"] == []


def test_collective_members_can_be_withdrawn(auth_client: APIClient) -> None:
    submission_id, nomination_id = _submission(auth_client)
    participant_id = _collective(auth_client, submission_id, nomination_id)
    url = f"/api/v1/submissions/{submission_id}/participants/{participant_id}/members"
    auth_client.put(url, {"members": ["Иванова Мария Петровна"]}, format="json")

    cleared = auth_client.put(url, {"members": []}, format="json")

    assert cleared.status_code == 200, cleared.data
    assert cleared.data["data"]["participants"][0]["members"] == []


def test_naming_members_keeps_the_participant_id(auth_client: APIClient) -> None:
    """A roster change is not a different participant — the client's id stays valid."""
    submission_id, nomination_id = _submission(auth_client)
    participant_id = _collective(auth_client, submission_id, nomination_id)

    saved = auth_client.put(
        f"/api/v1/submissions/{submission_id}/participants/{participant_id}/members",
        {"members": ["Иванова Мария Петровна"]},
        format="json",
    )

    assert str(saved.data["data"]["participants"][0]["id"]) == participant_id


def test_naming_members_of_an_unknown_participant_is_not_found(auth_client: APIClient) -> None:
    submission_id, nomination_id = _submission(auth_client)
    _collective(auth_client, submission_id, nomination_id)

    response = auth_client.put(
        f"/api/v1/submissions/{submission_id}/participants/{uuid7()}/members",
        {"members": ["Иванова Мария Петровна"]},
        format="json",
    )

    assert response.status_code == 404
