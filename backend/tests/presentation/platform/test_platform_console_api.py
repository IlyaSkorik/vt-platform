"""Integration tests for the platform operator's console.

The console is what sits above every organization: connecting new ones, setting
what each owes the platform, and reading the pipeline across all of them. Access
comes only from the ``grant_platform_admin`` command, so these tests grant it the
same way the deployment would.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.applications.infrastructure.models import ApplicationModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.infrastructure.models import OrganizationModel
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_ORGANIZATIONS = "/api/v1/platform/organizations"
_DASHBOARD = "/api/v1/platform/dashboard"


def _register(client: APIClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Илья", "lastName": "Скорик"},
        format="json",
    )
    user_id = registration.data["data"]["id"]
    access = str(identity_composition.build_token_service().issue(subject=user_id).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return str(user_id)


@pytest.fixture
def operator() -> APIClient:
    """A client authenticated as the platform operator (granted by command)."""
    client = APIClient()
    user_id = _register(client, "operator@example.com")
    build_grant_platform_administrator_handler().handle(GrantPlatformAdministratorCommand(user_id=user_id))
    return client


@pytest.fixture
def organization_owner() -> APIClient:
    """A client authenticated as the OWNER of the platform's own organization."""
    client = APIClient()
    user_id = _register(client, "owner@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    return client


def _order(*, competition_id: uuid.UUID, status: str, amount: str | None) -> ApplicationModel:
    return ApplicationModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status=status,
        total_price={"amount": amount, "currency": "BYN"} if amount is not None else None,
    )


class TestAccess:
    def test_an_anonymous_caller_is_refused(self) -> None:
        assert APIClient().get(_ORGANIZATIONS).status_code == 401

    def test_an_organization_owner_is_not_a_platform_operator(self, organization_owner: APIClient) -> None:
        # The whole point of the separation: the top of an organization is still
        # inside it, and the console that governs organizations is not theirs.
        assert organization_owner.get(_ORGANIZATIONS).status_code == 403
        assert organization_owner.get(_DASHBOARD).status_code == 403

    def test_the_operator_is_admitted(self, operator: APIClient) -> None:
        assert operator.get(_ORGANIZATIONS).status_code == 200


class TestConnectingAnOrganization:
    def test_connects_and_emails_the_owner_an_invitation(self, operator: APIClient) -> None:
        mail.outbox.clear()

        response = operator.post(
            _ORGANIZATIONS,
            {"name": "Звёздный дождь", "ownerEmail": "director@example.com", "commissionPercent": "12.5"},
            format="json",
        )

        assert response.status_code == 201, response.data
        data = response.data["data"]
        assert data["name"] == "Звёздный дождь"
        assert data["slug"] == "zvezdnyy-dozhd"  # transliterated from the name
        assert data["commissionPercent"] == "12.50"
        assert data["status"] == "ACTIVE"

        assert OrganizationModel.objects.filter(name="Звёздный дождь").exists()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["director@example.com"]

    def test_refuses_a_second_organization_at_the_same_address(self, operator: APIClient) -> None:
        payload = {"name": "Звёздный дождь", "ownerEmail": "a@example.com", "commissionPercent": "5"}
        assert operator.post(_ORGANIZATIONS, payload, format="json").status_code == 201

        clash = operator.post(
            _ORGANIZATIONS,
            {"name": "Звёздный дождь", "ownerEmail": "b@example.com", "commissionPercent": "5"},
            format="json",
        )
        assert clash.status_code == 409

    def test_lists_the_connected_organizations(self, operator: APIClient) -> None:
        operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        )
        listed = operator.get(_ORGANIZATIONS)
        assert listed.status_code == 200
        names = [row["name"] for row in listed.data["data"]]
        assert "Гармония" in names


class TestCommercialTerms:
    def test_changes_the_commission_rate(self, operator: APIClient) -> None:
        created = operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        ).data["data"]

        updated = operator.patch(f"{_ORGANIZATIONS}/{created['id']}", {"commissionPercent": "15"}, format="json")

        assert updated.status_code == 200, updated.data
        assert updated.data["data"]["commissionPercent"] == "15.00"

    def test_suspends_and_reactivates(self, operator: APIClient) -> None:
        created = operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        ).data["data"]
        url = f"{_ORGANIZATIONS}/{created['id']}"

        assert operator.patch(url, {"status": "SUSPENDED"}, format="json").data["data"]["status"] == "SUSPENDED"
        assert operator.patch(url, {"status": "ACTIVE"}, format="json").data["data"]["status"] == "ACTIVE"

    def test_an_empty_patch_is_refused(self, operator: APIClient) -> None:
        created = operator.post(
            _ORGANIZATIONS,
            {"name": "Гармония", "ownerEmail": "harmony@example.com", "commissionPercent": "7"},
            format="json",
        ).data["data"]
        assert operator.patch(f"{_ORGANIZATIONS}/{created['id']}", {}, format="json").status_code == 400


class TestDashboard:
    def _connected_with_a_festival(self, operator: APIClient, *, name: str, commission: str) -> tuple[str, CompetitionModel]:
        organization = operator.post(
            _ORGANIZATIONS,
            {"name": name, "ownerEmail": f"{uuid.uuid4().hex[:8]}@example.com", "commissionPercent": commission},
            format="json",
        ).data["data"]
        competition = CompetitionModel.objects.create(
            organizer_id=uuid.UUID(organization["id"]),
            status="PUBLISHED",
            title=f"{name} — сезон",
            season="2025/2026",
        )
        return organization["id"], competition

    def test_counts_applications_by_status_across_organizations(self, operator: APIClient) -> None:
        _, first = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _, second = self._connected_with_a_festival(operator, name="Созвездие", commission="20")
        _order(competition_id=first.id, status="SUBMITTED", amount="100.00")
        _order(competition_id=first.id, status="PAID", amount="200.00")
        _order(competition_id=second.id, status="CANCELLED", amount="500.00")

        data = operator.get(_DASHBOARD).data["data"]

        assert data["statusCounts"]["SUBMITTED"] == 1
        assert data["statusCounts"]["PAID"] == 1
        assert data["statusCounts"]["CANCELLED"] == 1
        assert data["applications"] == 3

    def test_projects_the_commission_from_the_fees(self, operator: APIClient) -> None:
        # A cancelled order is not revenue and must not inflate the projection;
        # a paid one counts towards both the expected and the settled figure.
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _order(competition_id=competition.id, status="SUBMITTED", amount="100.00")
        _order(competition_id=competition.id, status="PAID", amount="200.00")
        _order(competition_id=competition.id, status="CANCELLED", amount="500.00")

        data = operator.get(_DASHBOARD).data["data"]

        assert data["expectedFees"] == "300.00"
        assert data["settledFees"] == "200.00"
        assert data["expectedCommission"] == "30.00"
        assert data["settledCommission"] == "20.00"

    def test_filters_by_competition(self, operator: APIClient) -> None:
        _, wanted = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _, other = self._connected_with_a_festival(operator, name="Созвездие", commission="10")
        _order(competition_id=wanted.id, status="SUBMITTED", amount="100.00")
        _order(competition_id=other.id, status="SUBMITTED", amount="900.00")

        data = operator.get(f"{_DASHBOARD}?competitionId={wanted.id}").data["data"]

        assert data["applications"] == 1
        assert data["expectedFees"] == "100.00"

    def test_filters_by_organization(self, operator: APIClient) -> None:
        organization_id, wanted = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _, other = self._connected_with_a_festival(operator, name="Созвездие", commission="10")
        _order(competition_id=wanted.id, status="PAID", amount="100.00")
        _order(competition_id=other.id, status="PAID", amount="900.00")

        data = operator.get(f"{_DASHBOARD}?organizationId={organization_id}").data["data"]

        assert data["applications"] == 1
        assert [row["name"] for row in data["organizations"]] == ["Гармония"]

    def test_offers_the_competitions_to_filter_by(self, operator: APIClient) -> None:
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")

        data = operator.get(_DASHBOARD).data["data"]

        assert str(competition.id) in [option["id"] for option in data["competitions"]]

    def test_an_order_with_no_price_yet_counts_without_inventing_money(self, operator: APIClient) -> None:
        _, competition = self._connected_with_a_festival(operator, name="Гармония", commission="10")
        _order(competition_id=competition.id, status="SUBMITTED", amount=None)

        data = operator.get(_DASHBOARD).data["data"]

        assert data["applications"] == 1
        assert Decimal(data["expectedFees"]) == Decimal("0")
