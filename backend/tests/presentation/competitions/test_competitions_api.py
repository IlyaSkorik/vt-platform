"""Integration tests for the Competitions REST API v1 (organizer control panel).

Driven through DRF's ``APIClient`` against real PostgreSQL — the full edge is
exercised end to end (serializer → command → handler → repository → response).
Authentication uses a real JWT from the Identity login endpoint; staff status is
granted by provisioning the caller as the organization OWNER through the
Organization composition root (the same seam ``IsOrganizationStaff`` consults).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.competitions.infrastructure.system import Uuid7Generator
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


def _uuid7() -> uuid.UUID:
    return Uuid7Generator().new()


def _register_and_login(client: APIClient, email: str) -> str:
    client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Org", "lastName": "Aniser"},
        format="json",
    )
    login = client.post("/api/v1/auth/sessions", {"email": email, "password": _PASSWORD}, format="json")
    return str(login.data["data"]["accessToken"])


@pytest.fixture
def staff_client() -> APIClient:
    """An APIClient whose user is an active organization staff member (OWNER)."""
    client = APIClient()
    access = _register_and_login(client, "organizer@example.com")
    user_id = str(AccessToken(access)["user_id"])  # type: ignore[arg-type]
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def participant_client() -> APIClient:
    """An authenticated but non-staff APIClient (a participant)."""
    client = APIClient()
    access = _register_and_login(client, "participant@example.com")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def _create_competition(client: APIClient, **overrides: Any) -> Any:
    body: dict[str, Any] = {"organizerId": str(_uuid7()), "title": "Autumn Cup", "season": "2025/2026"}
    body.update(overrides)
    return client.post("/api/v1/competitions", body, format="json")


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_anonymous_is_rejected() -> None:
    response = APIClient().post("/api/v1/competitions", {}, format="json")
    assert response.status_code == 401


def test_participant_cannot_create_competition(participant_client: APIClient) -> None:
    response = _create_competition(participant_client)
    assert response.status_code == 403


def test_participant_cannot_list_competitions(participant_client: APIClient) -> None:
    assert participant_client.get("/api/v1/competitions").status_code == 403


# ---------------------------------------------------------------------------
# CRUD + validation
# ---------------------------------------------------------------------------


def test_staff_can_create_competition(staff_client: APIClient) -> None:
    response = _create_competition(staff_client)
    assert response.status_code == 201
    data = response.data["data"]
    assert data["status"] == "DRAFT"
    assert data["title"] == "Autumn Cup"
    # camelCase wire contract + envelope.
    assert "organizerId" in data
    assert "createdAt" in data
    assert response.data["meta"]["requestId"]


def test_create_validation_error_is_problem_json(staff_client: APIClient) -> None:
    response = staff_client.post("/api/v1/competitions", {"season": "2025/2026"}, format="json")
    assert response.status_code == 400
    assert response["content-type"] == "application/problem+json"
    assert response.data["status"] == 400


def test_get_unknown_competition_returns_404(staff_client: APIClient) -> None:
    response = staff_client.get(f"/api/v1/competitions/{_uuid7()}")
    assert response.status_code == 404
    assert response["content-type"] == "application/problem+json"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_open_registration_from_draft_is_conflict(staff_client: APIClient) -> None:
    """An illegal lifecycle transition (DRAFT → REGISTRATION_OPEN) is a 409."""
    competition_id = _create_competition(staff_client).data["data"]["id"]
    response = staff_client.post(f"/api/v1/competitions/{competition_id}/registration/open", {}, format="json")
    assert response.status_code == 409
    assert response["content-type"] == "application/problem+json"


def test_publish_incomplete_draft_is_unprocessable(staff_client: APIClient) -> None:
    """Publishing an unconfigured competition fails the publication-requirements gate (422)."""
    competition_id = _create_competition(staff_client).data["data"]["id"]
    response = staff_client.post(f"/api/v1/competitions/{competition_id}/publish", {}, format="json")
    assert response.status_code == 422
    assert response["content-type"] == "application/problem+json"


def test_mark_ready_incomplete_is_unprocessable(staff_client: APIClient) -> None:
    competition_id = _create_competition(staff_client).data["data"]["id"]
    staff_client.post(f"/api/v1/competitions/{competition_id}/configured", {}, format="json")
    response = staff_client.post(f"/api/v1/competitions/{competition_id}/ready", {}, format="json")
    assert response.status_code == 422


def test_full_organizer_workflow(staff_client: APIClient) -> None:
    base = "/api/v1/competitions"
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"{base}/{competition_id}"

    cat = staff_client.post(f"{detail}/categories", {"name": "Vocal"}, format="json")
    assert cat.status_code == 201
    category_id = cat.data["data"]["categories"][0]["id"]

    staff_client.post(f"{detail}/disciplines", {"categoryId": category_id, "name": "Solo"}, format="json")
    staff_client.post(f"{detail}/age-categories", {"categoryId": category_id, "name": "7-10", "minAge": 7, "maxAge": 10}, format="json")
    staff_client.post(f"{detail}/participant-groups", {"categoryId": category_id, "name": "Solo", "minCount": 1, "maxCount": 1}, format="json")
    view = staff_client.post(f"{detail}/participation-formats", {"name": "Очно"}, format="json").data["data"]

    combination = {
        "categoryId": view["categories"][0]["id"],
        "disciplineId": view["disciplines"][0]["id"],
        "ageCategoryId": view["ageCategories"][0]["id"],
        "participantGroupId": view["participantGroups"][0]["id"],
        "participationFormatId": view["participationFormats"][0]["id"],
    }
    staff_client.post(f"{detail}/admission-rules", combination, format="json")
    staff_client.post(f"{detail}/pricing-rules", {**combination, "amount": "50.00", "currency": "BYN"}, format="json")
    first = staff_client.post(
        f"{detail}/regulations",
        {"title": "Rules v1", "version": "1.0", "publicationDate": "2026-01-01", "fileReference": "s3://r1.pdf"},
        format="json",
    )
    first_regulation_id = first.data["data"]["regulations"][0]["id"]
    # A second regulation becomes current; switching back to the first is a real
    # state change that exercises the make-current endpoint (not a no-op).
    staff_client.post(
        f"{detail}/regulations",
        {"title": "Rules v2", "version": "2.0", "publicationDate": "2026-02-01", "fileReference": "s3://r2.pdf"},
        format="json",
    )
    made_current = staff_client.post(f"{detail}/regulations/{first_regulation_id}/current", {}, format="json")
    assert made_current.status_code == 200
    assert made_current.data["data"]["currentRegulationId"] == first_regulation_id

    assert staff_client.post(f"{detail}/configured", {}, format="json").status_code == 200
    assert staff_client.post(f"{detail}/ready", {}, format="json").status_code == 200
    published = staff_client.post(f"{detail}/publish", {}, format="json")
    assert published.status_code == 200
    assert published.data["data"]["status"] == "PUBLISHED"
    opened = staff_client.post(f"{detail}/registration/open", {}, format="json")
    assert opened.data["data"]["status"] == "REGISTRATION_OPEN"


# ---------------------------------------------------------------------------
# Routing regression: previously-shadowed detail methods are reachable
# ---------------------------------------------------------------------------


def test_rename_and_delete_category_are_both_reachable(staff_client: APIClient) -> None:
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"/api/v1/competitions/{competition_id}"
    category_id = staff_client.post(f"{detail}/categories", {"name": "Vocal"}, format="json").data["data"]["categories"][0]["id"]

    renamed = staff_client.patch(f"{detail}/categories/{category_id}", {"name": "Choir"}, format="json")
    assert renamed.status_code == 200
    assert renamed.data["data"]["categories"][0]["name"] == "Choir"

    removed = staff_client.delete(f"{detail}/categories/{category_id}")
    assert removed.status_code == 200
    assert removed.data["data"]["categories"] == []
