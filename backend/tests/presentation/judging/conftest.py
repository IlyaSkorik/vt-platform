"""Shared fixtures for the Judging REST suites.

Two clients, because the security boundary of this context is exactly the line between
them: :func:`staff_client` is the organizer, :func:`judge_client` is somebody with an
account and no staff membership at all. Most of what is asserted in these suites is
what the second one may and may not reach.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.application.handlers import SetOrganizationModulesCommand
from apps.organization.composition import (
    build_provision_owner_handler,
    build_set_organization_modules_handler,
)
from apps.organization.infrastructure.repositories import DjangoOrganizationRepository

_PASSWORD = "V3ry$ecurePass!"

SETUP = "/api/v1/staff/judging/setup"
JURY = "/api/v1/staff/judging/jury"


def organization_id() -> str:
    organization = DjangoOrganizationRepository().get_default()
    assert organization is not None
    return organization.id.json()


def set_modules(*modules: str) -> None:
    """Put the organization on exactly these modules."""
    build_set_organization_modules_handler().handle(SetOrganizationModulesCommand(organization_id=organization_id(), modules=modules))


def _register(client: APIClient, email: str) -> str:
    """Create an account and return the access token that authenticates it."""
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Тест", "lastName": "Пользователь"},
        format="json",
    )
    assert registration.status_code in {200, 201}, registration.data
    return str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)


@pytest.fixture
def staff_client() -> APIClient:
    """An APIClient whose user is the organization OWNER, holding every module."""
    client = APIClient()
    access = _register(client, "owner@example.com")
    user_id = str(AccessToken(access)["user_id"])  # type: ignore[arg-type]
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def judge_client() -> APIClient:
    """An authenticated account with **no** staff membership — a guest judge."""
    client = APIClient()
    access = _register(client, "judge@example.com")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def online_competition(staff_client: APIClient) -> dict[str, Any]:
    """A festival with one genre, judged online.

    Built through the real edge rather than through fixtures so the suite exercises the
    same path an organizer does — including the settings payload that carries the
    judging mode.
    """
    created = staff_client.post(
        "/api/v1/competitions",
        {"title": "Весна талантов", "season": "2026"},
        format="json",
    )
    assert created.status_code == 201, created.data
    competition_id = created.data["data"]["id"]

    category = staff_client.post(
        f"/api/v1/competitions/{competition_id}/categories",
        {"name": "Вокал"},
        format="json",
    )
    assert category.status_code in {200, 201}, category.data

    settings = staff_client.get(f"/api/v1/competitions/{competition_id}").data["data"]["settings"]
    updated = staff_client.put(
        f"/api/v1/competitions/{competition_id}/settings",
        {**settings, "judgingMode": "ONLINE"},
        format="json",
    )
    assert updated.status_code == 200, updated.data

    detail: dict[str, Any] = staff_client.get(f"/api/v1/competitions/{competition_id}").data["data"]
    return detail


@pytest.fixture
def competition_id(online_competition: dict[str, Any]) -> str:
    return str(online_competition["id"])


@pytest.fixture
def category_id(online_competition: dict[str, Any]) -> str:
    return str(online_competition["categories"][0]["id"])
