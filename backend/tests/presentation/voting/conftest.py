"""Shared fixtures for the Voting REST suites."""

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


def organization_id() -> str:
    organization = DjangoOrganizationRepository().get_default()
    assert organization is not None
    return organization.id.json()


def set_modules(*modules: str) -> None:
    """Put the organization on exactly these modules."""
    build_set_organization_modules_handler().handle(SetOrganizationModulesCommand(organization_id=organization_id(), modules=modules))


@pytest.fixture
def staff_client() -> APIClient:
    """An APIClient whose user is the organization OWNER, holding the voting module."""
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "owner@example.com", "password": _PASSWORD, "firstName": "Org", "lastName": "Owner"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    user_id = str(AccessToken(access)["user_id"])  # type: ignore[arg-type]
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def ballot(staff_client: APIClient) -> dict[str, Any]:
    """A standalone ballot with two nominees, still in draft."""
    created = staff_client.post("/api/v1/staff/ballots", {"title": "Приз зрительских симпатий"}, format="json")
    assert created.status_code == 201, created.data
    ballot_id = created.data["data"]["id"]
    for index, name in enumerate(("Ансамбль «Ритм»", "Хор «Родник»"), start=1):
        staff_client.post(
            f"/api/v1/staff/ballots/{ballot_id}/nominees",
            {"title": name, "number": index},
            format="json",
        )
    created_ballot: dict[str, Any] = staff_client.get(f"/api/v1/staff/ballots/{ballot_id}").data["data"]
    return created_ballot


@pytest.fixture
def open_ballot(staff_client: APIClient, ballot: dict[str, Any]) -> dict[str, Any]:
    """The same ballot, accepting votes."""
    opened = staff_client.post(f"/api/v1/staff/ballots/{ballot['id']}/open", format="json")
    assert opened.status_code == 200, opened.data
    running: dict[str, Any] = opened.data["data"]
    return running
