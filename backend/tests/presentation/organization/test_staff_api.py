"""Integration tests for the Organization staff-management REST API v1.

Driven through DRF's ``APIClient`` against real PostgreSQL — serializer →
command → handler → repository → response, end to end. The singleton
organization is seeded by the data migration; the primary OWNER is provisioned
through the composition root (the same seam authorization consults), and
additional active members are seeded directly through the repositories.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.value_objects import StaffMembershipId, StaffRole, StaffUserId
from apps.organization.infrastructure.repositories import (
    DjangoOrganizationRepository,
    DjangoStaffMembershipRepository,
)
from apps.organization.infrastructure.system import SystemClock

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_INVITATIONS_URL = "/api/v1/staff/invitations"
_MEMBERS_URL = "/api/v1/staff/members"


def _register_and_login(client: APIClient, email: str) -> tuple[str, str]:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Org", "lastName": "Aniser"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    user_id = str(AccessToken(access)["user_id"])  # type: ignore[arg-type]
    return access, user_id


def _seed_active_member(user_id: str, role: StaffRole) -> str:
    """Seed an ACTIVE membership for ``user_id`` with ``role``; return its id."""
    now = SystemClock().utcnow()
    org = DjangoOrganizationRepository().get_default()
    assert org is not None
    uid = StaffUserId.from_string(user_id)
    membership = StaffMembership.pending_from_invitation(
        membership_id=StaffMembershipId.generate(),
        organization_id=org.id,
        user_id=uid,
        role=role,
        invited_by=uid,
        invited_at=now,
        now=now,
    )
    membership.activate(accepted_by=uid, now=now)
    DjangoStaffMembershipRepository().save(membership)
    return membership.id.json()


@pytest.fixture
def owner_client() -> APIClient:
    """An APIClient whose user is the active organization OWNER."""
    client = APIClient()
    access, user_id = _register_and_login(client, "owner@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def _member_client(email: str, role: StaffRole) -> tuple[APIClient, str]:
    """An active staff APIClient with ``role``, plus its membership id."""
    client = APIClient()
    access, user_id = _register_and_login(client, email)
    membership_id = _seed_active_member(user_id, role)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client, membership_id


@pytest.fixture
def participant_client() -> APIClient:
    """An authenticated but non-staff APIClient."""
    client = APIClient()
    access, _ = _register_and_login(client, "participant@example.com")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_anonymous_is_rejected() -> None:
    assert APIClient().get(_INVITATIONS_URL).status_code == 401
    assert APIClient().get(_MEMBERS_URL).status_code == 401


def test_participant_cannot_list_invitations(participant_client: APIClient) -> None:
    assert participant_client.get(_INVITATIONS_URL).status_code == 403


def test_support_can_read_but_not_manage() -> None:
    support, _ = _member_client("support@example.com", StaffRole.SUPPORT)
    assert support.get(_INVITATIONS_URL).status_code == 200
    assert support.get(_MEMBERS_URL).status_code == 200
    # A non-admin staff member cannot create an invitation.
    forbidden = support.post(
        _INVITATIONS_URL, {"email": "new@example.com", "role": "SUPPORT"}, format="json"
    )
    assert forbidden.status_code == 403


# ---------------------------------------------------------------------------
# Invitations: create / list / revoke
# ---------------------------------------------------------------------------


def test_owner_creates_lists_and_revokes_invitation(owner_client: APIClient) -> None:
    created = owner_client.post(
        _INVITATIONS_URL, {"email": "invitee@example.com", "role": "MODERATOR"}, format="json"
    )
    assert created.status_code == 201
    invitation = created.data["data"]
    assert invitation["email"] == "invitee@example.com"
    assert invitation["status"] == "pending"
    invitation_id = invitation["id"]

    listing = owner_client.get(_INVITATIONS_URL)
    assert listing.status_code == 200
    assert any(item["id"] == invitation_id for item in listing.data["data"])

    revoked = owner_client.post(f"{_INVITATIONS_URL}/{invitation_id}/revoke")
    assert revoked.status_code == 200
    assert revoked.data["data"]["status"] == "revoked"

    # Revoking again conflicts.
    assert owner_client.post(f"{_INVITATIONS_URL}/{invitation_id}/revoke").status_code == 409


def test_revoke_unknown_invitation_is_404(owner_client: APIClient) -> None:
    missing = "01900000-0000-7000-8000-0000000000ff"
    assert owner_client.post(f"{_INVITATIONS_URL}/{missing}/revoke").status_code == 404


def test_director_may_invite() -> None:
    director, _ = _member_client("director@example.com", StaffRole.DIRECTOR)
    created = director.post(
        _INVITATIONS_URL, {"email": "bydirector@example.com", "role": "SUPPORT"}, format="json"
    )
    assert created.status_code == 201


# ---------------------------------------------------------------------------
# Members: list / change role / revoke
# ---------------------------------------------------------------------------


def test_owner_lists_members(owner_client: APIClient) -> None:
    _member_client("member@example.com", StaffRole.SUPPORT)
    listing = owner_client.get(_MEMBERS_URL)
    assert listing.status_code == 200
    emails = {row["email"] for row in listing.data["data"]}
    assert "owner@example.com" in emails
    assert "member@example.com" in emails
    owner_row = next(row for row in listing.data["data"] if row["email"] == "owner@example.com")
    assert owner_row["role"] == "OWNER"
    assert owner_row["status"] == "ACTIVE"
    assert owner_row["displayName"]


def test_owner_changes_member_role(owner_client: APIClient) -> None:
    _, membership_id = _member_client("tochange@example.com", StaffRole.SUPPORT)
    response = owner_client.patch(
        f"{_MEMBERS_URL}/{membership_id}", {"role": "MODERATOR"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["data"]["role"] == "MODERATOR"

    row = next(r for r in owner_client.get(_MEMBERS_URL).data["data"] if r["id"] == membership_id)
    assert row["role"] == "MODERATOR"


def test_owner_revokes_member(owner_client: APIClient) -> None:
    _, membership_id = _member_client("torevoke@example.com", StaffRole.SUPPORT)
    response = owner_client.post(f"{_MEMBERS_URL}/{membership_id}/revoke")
    assert response.status_code == 200
    assert response.data["data"]["status"] == "REVOKED"


def test_cannot_revoke_last_owner(owner_client: APIClient) -> None:
    owner_id = next(
        row["id"] for row in owner_client.get(_MEMBERS_URL).data["data"] if row["role"] == "OWNER"
    )
    response = owner_client.post(f"{_MEMBERS_URL}/{owner_id}/revoke")
    assert response.status_code == 409


def test_cannot_demote_last_owner(owner_client: APIClient) -> None:
    owner_id = next(
        row["id"] for row in owner_client.get(_MEMBERS_URL).data["data"] if row["role"] == "OWNER"
    )
    response = owner_client.patch(f"{_MEMBERS_URL}/{owner_id}", {"role": "DIRECTOR"}, format="json")
    assert response.status_code == 409


def test_support_cannot_change_roles(owner_client: APIClient) -> None:
    support, _ = _member_client("support2@example.com", StaffRole.SUPPORT)
    _, target_id = _member_client("target@example.com", StaffRole.SUPPORT)
    response = support.patch(f"{_MEMBERS_URL}/{target_id}", {"role": "MODERATOR"}, format="json")
    assert response.status_code == 403


def test_change_role_invalid_role_is_400(owner_client: APIClient) -> None:
    _, membership_id = _member_client("badrole@example.com", StaffRole.SUPPORT)
    response = owner_client.patch(
        f"{_MEMBERS_URL}/{membership_id}", {"role": "SUPREME_LEADER"}, format="json"
    )
    assert response.status_code == 400
