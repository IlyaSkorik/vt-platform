"""Unit tests for the Organization domain aggregate roots."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from apps.organization.domain.entities import (
    Organization,
    StaffInvitation,
    StaffMembership,
)
from apps.organization.domain.events import (
    OrganizationSeeded,
    StaffInvitationAccepted,
    StaffMembershipActivated,
    StaffMembershipRevoked,
)
from apps.organization.domain.exceptions import (
    DirectConstructionError,
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationRevokedError,
    MembershipAlreadyActiveError,
    MembershipAlreadyRevokedError,
    MembershipNotPendingError,
)
from apps.organization.domain.policies import InvitationExpiryPolicy
from apps.organization.domain.value_objects import (
    InvitationTokenHash,
    MembershipStatus,
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
    OrganizationStatus,
    StaffEmail,
    StaffInvitationId,
    StaffMembershipId,
    StaffRole,
    StaffUserId,
)

NOW = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)


def _org() -> Organization:
    org, _ = Organization.seed(
        organization_id=OrganizationId.generate(),
        name=OrganizationName("Взлёт талантов"),
        slug=OrganizationSlug("vzlyot-talantov"),
        now=NOW,
    )
    return org


def _user() -> StaffUserId:
    return StaffUserId.from_uuid(OrganizationId.generate().value)


class TestOrganization:
    def test_seed_is_active_and_emits_event(self) -> None:
        org, events = Organization.seed(
            organization_id=OrganizationId.generate(),
            name=OrganizationName("Взлёт талантов"),
            slug=OrganizationSlug("vzlyot-talantov"),
            now=NOW,
        )
        assert org.is_active()
        assert isinstance(events[0], OrganizationSeeded)

    def test_direct_construction_forbidden(self) -> None:
        with pytest.raises(DirectConstructionError):
            Organization(
                _token=object(),
                _id=OrganizationId.generate(),
                _name=OrganizationName("x"),
                _slug=OrganizationSlug("x"),
                _status=OrganizationStatus.ACTIVE,
                _created_at=NOW,
                _updated_at=NOW,
            )

    def test_suspend_then_reactivate(self) -> None:
        org = _org()
        org.suspend(now=NOW)
        assert not org.is_active()
        org.reactivate(now=NOW)
        assert org.is_active()
        assert org.version == 3  # seed=1, suspend=2, reactivate=3


class TestStaffMembership:
    def test_activate_for_owner_is_active_owner(self) -> None:
        m, events = StaffMembership.activate_for_owner(
            membership_id=StaffMembershipId.generate(),
            organization_id=OrganizationId.generate(),
            user_id=_user(),
            now=NOW,
        )
        assert m.role is StaffRole.OWNER
        assert m.is_active()
        assert m.has_role(StaffRole.OWNER)
        assert isinstance(events[0], StaffMembershipActivated)

    def test_pending_activation_and_audit(self) -> None:
        inviter = _user()
        m = StaffMembership.pending_from_invitation(
            membership_id=StaffMembershipId.generate(),
            organization_id=OrganizationId.generate(),
            user_id=_user(),
            role=StaffRole.MODERATOR,
            invited_by=inviter,
            invited_at=NOW,
            now=NOW,
        )
        assert m.status is MembershipStatus.PENDING
        assert m.invited_by == inviter
        events = m.activate(accepted_by=m.user_id, now=NOW)
        assert m.is_active()
        assert m.accepted_at == NOW
        assert isinstance(events[0], StaffMembershipActivated)

    def test_cannot_activate_twice(self) -> None:
        m, _ = StaffMembership.activate_for_owner(
            membership_id=StaffMembershipId.generate(),
            organization_id=OrganizationId.generate(),
            user_id=_user(),
            now=NOW,
        )
        with pytest.raises(MembershipAlreadyActiveError):
            m.activate(accepted_by=m.user_id, now=NOW)

    def test_revoke_records_who(self) -> None:
        revoker = _user()
        m, _ = StaffMembership.activate_for_owner(
            membership_id=StaffMembershipId.generate(),
            organization_id=OrganizationId.generate(),
            user_id=_user(),
            now=NOW,
        )
        events = m.revoke(revoked_by=revoker, now=NOW)
        assert m.status is MembershipStatus.REVOKED
        assert m.revoked_by == revoker
        assert not m.has_role(StaffRole.OWNER)
        assert isinstance(events[0], StaffMembershipRevoked)
        with pytest.raises(MembershipAlreadyRevokedError):
            m.revoke(revoked_by=revoker, now=NOW)

    def test_change_role_noop_returns_no_events(self) -> None:
        m, _ = StaffMembership.activate_for_owner(
            membership_id=StaffMembershipId.generate(),
            organization_id=OrganizationId.generate(),
            user_id=_user(),
            now=NOW,
        )
        assert m.change_role(StaffRole.OWNER, changed_by=_user(), now=NOW) == []

    def test_change_role_on_pending_rejected(self) -> None:
        m = StaffMembership.pending_from_invitation(
            membership_id=StaffMembershipId.generate(),
            organization_id=OrganizationId.generate(),
            user_id=_user(),
            role=StaffRole.SUPPORT,
            invited_by=_user(),
            invited_at=NOW,
            now=NOW,
        )
        with pytest.raises(MembershipNotPendingError):
            m.change_role(StaffRole.MODERATOR, changed_by=_user(), now=NOW)


class TestStaffInvitation:
    def _issue(self, policy: InvitationExpiryPolicy | None = None) -> StaffInvitation:
        policy = policy or InvitationExpiryPolicy()
        invitation, _ = StaffInvitation.issue(
            invitation_id=StaffInvitationId.generate(),
            organization_id=OrganizationId.generate(),
            email=StaffEmail("staff@example.com"),
            role=StaffRole.MODERATOR,
            token_hash=InvitationTokenHash("a" * 64),
            raw_token="raw-token",
            invited_by=_user(),
            policy=policy,
            now=NOW,
        )
        return invitation

    def test_issue_sets_expiry_from_policy(self) -> None:
        inv = self._issue(InvitationExpiryPolicy(ttl=timedelta(days=3)))
        assert inv.expires_at == NOW + timedelta(days=3)
        assert inv.is_pending()

    def test_accept_marks_accepted_and_emits(self) -> None:
        inv = self._issue()
        events = inv.accept(accepted_by=_user(), policy=InvitationExpiryPolicy(), now=NOW)
        assert not inv.is_pending()
        assert isinstance(events[0], StaffInvitationAccepted)

    def test_cannot_accept_twice(self) -> None:
        inv = self._issue()
        inv.accept(accepted_by=_user(), policy=InvitationExpiryPolicy(), now=NOW)
        with pytest.raises(InvitationAlreadyAcceptedError):
            inv.accept(accepted_by=_user(), policy=InvitationExpiryPolicy(), now=NOW)

    def test_expired_invitation_rejected(self) -> None:
        policy = InvitationExpiryPolicy(ttl=timedelta(days=1))
        inv = self._issue(policy)
        later = NOW + timedelta(days=2)
        with pytest.raises(InvitationExpiredError):
            inv.accept(accepted_by=_user(), policy=policy, now=later)

    def test_revoked_invitation_cannot_be_accepted(self) -> None:
        inv = self._issue()
        inv.revoke(revoked_by=_user(), now=NOW)
        with pytest.raises(InvitationRevokedError):
            inv.accept(accepted_by=_user(), policy=InvitationExpiryPolicy(), now=NOW)
