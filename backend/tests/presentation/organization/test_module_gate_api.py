"""The module gate at the HTTP edge.

An organization that was sold only the audience vote must not merely have the
festival machinery hidden from it — it must be refused by the API. These tests
drive that through the real edge: switch a module off in the platform console's
use case, then knock on the endpoint it guards.
"""

from __future__ import annotations

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

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_COMPETITIONS = "/api/v1/competitions"
_PROGRAMS = "/api/v1/staff/programs"
_TEMPLATES = "/api/v1/staff/diplomas/templates"
_ME = "/api/v1/users/me"


def _organization_id() -> str:
    organization = DjangoOrganizationRepository().get_default()
    assert organization is not None
    return organization.id.json()


def _set_modules(*modules: str) -> None:
    build_set_organization_modules_handler().handle(SetOrganizationModulesCommand(organization_id=_organization_id(), modules=modules))


@pytest.fixture
def owner_client() -> APIClient:
    """An APIClient whose user is the active organization OWNER."""
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


class TestAVotingOnlyOrganization:
    def test_the_festival_endpoint_is_refused(self, owner_client: APIClient) -> None:
        _set_modules("VOTING")

        response = owner_client.get(_COMPETITIONS)

        assert response.status_code == 403

    def test_the_programme_endpoint_is_refused(self, owner_client: APIClient) -> None:
        _set_modules("VOTING")

        assert owner_client.get(_PROGRAMS).status_code == 403

    def test_the_diploma_library_is_refused(self, owner_client: APIClient) -> None:
        _set_modules("VOTING")

        assert owner_client.get(_TEMPLATES).status_code == 403

    def test_the_refusal_says_which_thing_is_missing(self, owner_client: APIClient) -> None:
        """403 and a sentence the organizer can act on — not a bare 404."""
        _set_modules("VOTING")

        response = owner_client.get(_COMPETITIONS)

        assert "не подключён" in str(response.data["detail"])

    def test_switching_the_module_back_on_reopens_the_endpoint(self, owner_client: APIClient) -> None:
        _set_modules("VOTING")
        assert owner_client.get(_COMPETITIONS).status_code == 403

        _set_modules("VOTING", "COMPETITIONS")

        assert owner_client.get(_COMPETITIONS).status_code == 200

    def test_the_organizations_own_profile_is_never_gated(self, owner_client: APIClient) -> None:
        """Profile, staff and settings are not modules: an organization always has them."""
        _set_modules()

        assert owner_client.get("/api/v1/organization/profile").status_code == 200


class TestTheCurrentUserPayload:
    def test_it_carries_the_modules_the_organization_holds(self, owner_client: APIClient) -> None:
        _set_modules("VOTING", "PROGRAMS")

        response = owner_client.get(_ME)

        assert response.status_code == 200
        assert response.data["data"]["enabledModules"] == ["PROGRAMS", "VOTING"]

    def test_a_non_staff_user_holds_no_modules(self) -> None:
        client = APIClient()
        registration = client.post(
            "/api/v1/auth/registration",
            {"email": "participant@example.com", "password": _PASSWORD, "firstName": "Just", "lastName": "Aperson"},
            format="json",
        )
        access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.get(_ME)

        assert response.status_code == 200
        assert response.data["data"]["enabledModules"] == []
