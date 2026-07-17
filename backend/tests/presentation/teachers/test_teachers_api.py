"""Integration tests for the Teacher Directory REST API v1.

Driven through DRF's ``APIClient`` against real PostgreSQL - the full edge end to
end (serializer -> command -> handler -> repository -> response), with authentication
established by a real JWT issued from the Identity login endpoint. The repointing to
PostgreSQL is done by ``tests/presentation/conftest.py``.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.identity.presentation.api.v1.auth import composition as identity_composition

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


@pytest.fixture
def client() -> APIClient:
    return APIClient()


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
def auth_client(client: APIClient) -> APIClient:
    return _auth(client, email="owner@example.com")


def _add(client: APIClient, **overrides: Any) -> Any:
    body: dict[str, Any] = {"firstName": "Anna", "lastName": "Ivanova", "role": "Teacher"}
    body.update(overrides)
    return client.post("/api/v1/teachers", body, format="json")


def test_requires_authentication(client: APIClient) -> None:
    assert client.get("/api/v1/teachers").status_code == 401


def test_add_returns_resource_envelope(auth_client: APIClient) -> None:
    response = _add(auth_client, middleName="Petrovna", email="anna@school.ru", phone="+79991234567", role="Choreographer")
    assert response.status_code == 201
    data = response.data["data"]
    assert data["type"] == "teacher"
    assert data["displayName"] == "Ivanova Anna Petrovna"
    assert data["role"] == "Choreographer"
    assert data["status"] == "ACTIVE"
    assert response["Location"].startswith("/api/v1/teachers/")
    assert response.data["meta"]["requestId"]


def test_add_rejects_bad_email(auth_client: APIClient) -> None:
    response = _add(auth_client, email="not-an-email")
    assert response.status_code == 400
    assert response["Content-Type"] == "application/problem+json"


def test_directory_lists_active_and_hides_archived(auth_client: APIClient) -> None:
    keep = _add(auth_client, firstName="Anna").data["data"]["id"]
    drop = _add(auth_client, firstName="Boris").data["data"]["id"]
    assert auth_client.post(f"/api/v1/teachers/{drop}/archival").status_code == 200

    active = auth_client.get("/api/v1/teachers")
    ids = [t["id"] for t in active.data["data"]]
    assert keep in ids
    assert drop not in ids

    with_archived = auth_client.get("/api/v1/teachers?includeArchived=true")
    ids_all = [t["id"] for t in with_archived.data["data"]]
    assert keep in ids_all
    assert drop in ids_all


def test_update_and_retrieve(auth_client: APIClient) -> None:
    teacher_id = _add(auth_client).data["data"]["id"]
    updated = auth_client.patch(
        f"/api/v1/teachers/{teacher_id}",
        {"firstName": "Anna", "lastName": "Sidorova", "role": "Director"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["data"]["lastName"] == "Sidorova"
    fetched = auth_client.get(f"/api/v1/teachers/{teacher_id}")
    assert fetched.data["data"]["role"] == "Director"


def test_archive_then_reactivate(auth_client: APIClient) -> None:
    teacher_id = _add(auth_client).data["data"]["id"]
    assert auth_client.post(f"/api/v1/teachers/{teacher_id}/archival").data["data"]["status"] == "ARCHIVED"
    # Archiving again is an illegal transition -> 409.
    assert auth_client.post(f"/api/v1/teachers/{teacher_id}/archival").status_code == 409
    assert auth_client.post(f"/api/v1/teachers/{teacher_id}/reactivation").data["data"]["status"] == "ACTIVE"


def test_directory_is_scoped_to_owner(client: APIClient) -> None:
    owner = _auth(APIClient(), email="owner-a@example.com")
    teacher_id = _add(owner).data["data"]["id"]
    other = _auth(APIClient(), email="owner-b@example.com")
    # Another user sees an empty directory and cannot fetch the entry.
    assert other.get("/api/v1/teachers").data["data"] == []
    assert other.get(f"/api/v1/teachers/{teacher_id}").status_code == 404
