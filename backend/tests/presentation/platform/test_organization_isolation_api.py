"""The boundary between two connected organizations.

Connecting a second organization is only safe if its people cannot see the first
one's work. These tests drive both sides through the real HTTP edge: two
organizations, two owners, one festival each, and every crossing refused.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.applications.infrastructure.models import ApplicationModel
from apps.competitions.infrastructure.models import CompetitionModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.value_objects import OrganizationId, StaffMembershipId, StaffUserId
from apps.organization.infrastructure.repositories import DjangoStaffMembershipRepository
from apps.organization.infrastructure.system import SystemClock
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_COMPETITIONS = "/api/v1/competitions"
_WORKSPACE = "/api/v1/staff/applications/workspace"
_ARCHIVE = "/api/v1/staff/applications/documents.zip"
_ORGANIZATIONS = "/api/v1/platform/organizations"


def _register(client: APIClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Имя", "lastName": "Фамилия"},
        format="json",
    )
    user_id = registration.data["data"]["id"]
    access = str(identity_composition.build_token_service().issue(subject=user_id).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return str(user_id)


def _make_owner_of(user_id: str, organization_id: str) -> None:
    """Activate an OWNER membership directly — the invitation flow's end state."""
    membership, _ = StaffMembership.activate_for_owner(
        membership_id=StaffMembershipId.generate(),
        organization_id=OrganizationId.from_string(organization_id),
        user_id=StaffUserId.from_string(user_id),
        now=SystemClock().utcnow(),
    )
    DjangoStaffMembershipRepository().save(membership)


@pytest.fixture
def operator() -> APIClient:
    client = APIClient()
    user_id = _register(client, "operator@example.com")
    build_grant_platform_administrator_handler().handle(GrantPlatformAdministratorCommand(user_id=user_id))
    return client


@pytest.fixture
def first_organization(operator: APIClient) -> APIClient:
    """The platform's own organization, with its owner signed in."""
    client = APIClient()
    user_id = _register(client, "first-owner@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    return client


@pytest.fixture
def second_organization(operator: APIClient) -> tuple[APIClient, str]:
    """A newly connected organization, with its owner signed in."""
    organization = operator.post(
        _ORGANIZATIONS,
        {"name": "Созвездие", "ownerEmail": "second-owner@example.com", "commissionPercent": "10"},
        format="json",
    ).data["data"]
    client = APIClient()
    user_id = _register(client, "second-owner@example.com")
    _make_owner_of(user_id, organization["id"])
    return client, organization["id"]


def _create_competition(client: APIClient, title: str) -> str:
    response = client.post(_COMPETITIONS, {"title": title, "season": "2025/2026"}, format="json")
    assert response.status_code == 201, response.data
    return str(response.data["data"]["id"])


class TestCompetitionsAreScopedToTheirOrganization:
    def test_a_competition_is_filed_under_the_creators_organization(self, second_organization) -> None:
        client, organization_id = second_organization
        competition_id = _create_competition(client, "Созвездие — сезон")

        stored = CompetitionModel.objects.get(id=competition_id)
        assert str(stored.organizer_id) == organization_id

    def test_the_list_shows_only_the_callers_own(self, first_organization, second_organization) -> None:
        client, _ = second_organization
        _create_competition(first_organization, "Взлёт — сезон")
        _create_competition(client, "Созвездие — сезон")

        first_titles = [row["title"] for row in first_organization.get(_COMPETITIONS).data["data"]]
        second_titles = [row["title"] for row in client.get(_COMPETITIONS).data["data"]]

        assert "Взлёт — сезон" in first_titles
        assert "Созвездие — сезон" not in first_titles
        assert second_titles == ["Созвездие — сезон"]

    def test_reaching_another_organizations_competition_is_refused(self, first_organization, second_organization) -> None:
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")

        assert client.get(f"{_COMPETITIONS}/{theirs}").status_code == 403
        assert client.post(f"{_COMPETITIONS}/{theirs}/categories", {"name": "Вокал"}, format="json").status_code == 403

    def test_the_platform_operator_reads_across_organizations_from_their_own_console(
        self, operator, first_organization, second_organization
    ) -> None:
        # Not through the organizer API: that one belongs to an organization's
        # staff, and the operator is staff of none. Their view of everything is
        # the platform console, which is read-only about other people's festivals.
        client, _ = second_organization
        _create_competition(first_organization, "Взлёт — сезон")
        _create_competition(client, "Созвездие — сезон")

        assert operator.get(_COMPETITIONS).status_code == 403

        titles = [option["title"] for option in operator.get("/api/v1/platform/dashboard").data["data"]["competitions"]]
        assert {"Взлёт — сезон", "Созвездие — сезон"} <= set(titles)


class TestApplicationsAreScopedToTheirOrganization:
    def _order_for(self, competition_id: str) -> None:
        ApplicationModel.objects.create(
            competition_id=uuid.UUID(competition_id),
            applicant_id=uuid.uuid4(),
            status="SUBMITTED",
            total_price={"amount": "100.00", "currency": "BYN"},
        )

    def test_the_workspace_offers_only_the_callers_competitions(self, first_organization, second_organization) -> None:
        client, _ = second_organization
        _create_competition(first_organization, "Взлёт — сезон")
        _create_competition(client, "Созвездие — сезон")

        data = client.get(_WORKSPACE).data["data"]
        titles = [row["title"] for row in data["filters"]["competitions"]] if "filters" in data else []

        assert "Взлёт — сезон" not in titles

    def test_the_paperwork_archive_stops_at_the_organization_boundary(self, first_organization, second_organization) -> None:
        client, _ = second_organization
        theirs = _create_competition(first_organization, "Взлёт — сезон")
        self._order_for(theirs)

        response = client.get(f"{_ARCHIVE}?competitionId={theirs}")

        assert response.status_code == 200
        # Nothing of the other organization's — the filter cannot widen the scope.
        assert b"".join(response.streaming_content)
