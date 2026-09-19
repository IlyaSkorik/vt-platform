"""Shared fixtures for the Reviews REST suites."""

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
from apps.organization.domain.value_objects import OrganizationModule
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
    """An APIClient whose user is the organization OWNER, holding the reviews module."""
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "owner@example.com", "password": _PASSWORD, "firstName": "Org", "lastName": "Owner"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    user_id = str(AccessToken(access)["user_id"])  # type: ignore[arg-type]
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    # Granted explicitly: reviews arrived after the migration that handed every
    # module to the organizations that already existed, so the seeded one does not
    # hold it — which is exactly the behaviour the module-gate test relies on.
    set_modules(*(module.value for module in OrganizationModule))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def page(staff_client: APIClient) -> dict[str, Any]:
    """The organization's review page, minted by the first read of it."""
    response = staff_client.get("/api/v1/staff/reviews/page")
    assert response.status_code == 200, response.data
    minted: dict[str, Any] = response.data["data"]
    return minted


@pytest.fixture(autouse=True)
def _media_in_tmp(settings: Any, tmp_path: Any) -> None:
    """Keep uploaded photographs out of the developer's media directory."""
    settings.MEDIA_ROOT = str(tmp_path)
