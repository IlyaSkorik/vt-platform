"""The platform operator's module switchboard, through the real HTTP edge."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.infrastructure.repositories import DjangoOrganizationRepository
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_ORGANIZATIONS = "/api/v1/platform/organizations"


def _organization_id() -> str:
    organization = DjangoOrganizationRepository().get_default()
    assert organization is not None
    return organization.id.json()


def _modules_url(organization_id: str | None = None) -> str:
    return f"{_ORGANIZATIONS}/{organization_id or _organization_id()}/modules"


@pytest.fixture
def operator_client() -> APIClient:
    """An APIClient whose user operates the platform itself."""
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "operator@example.com", "password": _PASSWORD, "firstName": "Plat", "lastName": "Operator"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    user_id = str(AccessToken(access)["user_id"])  # type: ignore[arg-type]
    build_grant_platform_administrator_handler().handle(GrantPlatformAdministratorCommand(user_id=user_id))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


class TestReadingTheSwitchboard:
    def test_it_lists_every_module_the_platform_knows(self, operator_client: APIClient) -> None:
        response = operator_client.get(_modules_url())

        assert response.status_code == 200
        names = [row["module"] for row in response.data["data"]["modules"]]
        assert "VOTING" in names
        assert len(names) == len(set(names))

    def test_an_unknown_organization_is_a_404(self, operator_client: APIClient) -> None:
        response = operator_client.get(_modules_url("0195c0de-dead-7000-8000-000000000000"))

        assert response.status_code == 404


class TestMovingTheSwitches:
    def test_a_put_replaces_the_whole_set(self, operator_client: APIClient) -> None:
        response = operator_client.put(_modules_url(), {"modules": ["VOTING"]}, format="json")

        assert response.status_code == 200
        enabled = {row["module"] for row in response.data["data"]["modules"] if row["enabled"]}
        assert enabled == {"VOTING"}

    def test_an_empty_set_is_honoured_rather_than_refused(self, operator_client: APIClient) -> None:
        response = operator_client.put(_modules_url(), {"modules": []}, format="json")

        assert response.status_code == 200
        assert not [row for row in response.data["data"]["modules"] if row["enabled"]]

    def test_an_unknown_module_is_refused(self, operator_client: APIClient) -> None:
        response = operator_client.put(_modules_url(), {"modules": ["TELEPATHY"]}, format="json")

        assert response.status_code == 400

    def test_re_sending_the_same_set_keeps_the_connection_date(self, operator_client: APIClient) -> None:
        first = operator_client.put(_modules_url(), {"modules": ["VOTING"]}, format="json")
        was = {row["module"]: row["enabledAt"] for row in first.data["data"]["modules"]}["VOTING"]

        second = operator_client.put(_modules_url(), {"modules": ["VOTING"]}, format="json")
        now = {row["module"]: row["enabledAt"] for row in second.data["data"]["modules"]}["VOTING"]

        assert now == was

    def test_a_withheld_module_records_when_it_was_withdrawn(self, operator_client: APIClient) -> None:
        response = operator_client.put(_modules_url(), {"modules": ["VOTING"]}, format="json")

        withheld = {row["module"]: row for row in response.data["data"]["modules"]}["FINANCE"]
        assert withheld["enabled"] is False
        assert withheld["disabledAt"] is not None


class TestConnectingWithAPreset:
    def test_an_organization_can_be_connected_holding_one_module(self, operator_client: APIClient) -> None:
        created = operator_client.post(
            _ORGANIZATIONS,
            {"name": "Только голосование", "ownerEmail": "owner@voting.example", "modules": ["VOTING"]},
            format="json",
        )
        assert created.status_code == 201

        response = operator_client.get(_modules_url(created.data["data"]["id"]))

        enabled = {row["module"] for row in response.data["data"]["modules"] if row["enabled"]}
        assert enabled == {"VOTING"}

    def test_connecting_without_naming_modules_grants_full_access(self, operator_client: APIClient) -> None:
        created = operator_client.post(
            _ORGANIZATIONS,
            {"name": "Полный доступ", "ownerEmail": "owner@full.example"},
            format="json",
        )

        response = operator_client.get(_modules_url(created.data["data"]["id"]))

        assert all(row["enabled"] for row in response.data["data"]["modules"])


class TestAuthorization:
    def test_an_ordinary_user_cannot_read_the_switchboard(self) -> None:
        client = APIClient()
        registration = client.post(
            "/api/v1/auth/registration",
            {"email": "nobody@example.com", "password": _PASSWORD, "firstName": "No", "lastName": "Body"},
            format="json",
        )
        access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        assert client.get(_modules_url()).status_code == 403
