"""Tests for the staff-management use cases: invitation roster/revoke and
membership roster / role-change / revoke (including the last-owner guard)."""

from __future__ import annotations

import pytest

from apps.organization.application.dto.commands import (
    ChangeStaffRoleCommand,
    RevokeStaffInvitationCommand,
    RevokeStaffMembershipCommand,
)
from apps.organization.application.dto.queries import (
    ListStaffInvitationsQuery,
    ListStaffMembersQuery,
)
from apps.organization.application.exceptions import (
    InvitationStateConflictError,
    LastOwnerError,
    MembershipStateConflictError,
    PermissionDeniedError,
    StaffInvitationNotFoundError,
    StaffMembershipNotFoundError,
)
from apps.organization.application.handlers import (
    ChangeStaffRoleHandler,
    ListStaffInvitationsHandler,
    ListStaffMembersHandler,
    RevokeStaffInvitationHandler,
    RevokeStaffMembershipHandler,
)
from apps.organization.domain.entities import Organization, StaffMembership
from apps.organization.domain.value_objects import (
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
    StaffEmail,
    StaffMembershipId,
    StaffRole,
    StaffUserId,
)

from .fakes import (
    NOW,
    FakeClock,
    FakeOrganizationRepository,
    FakeStaffInvitationRepository,
    FakeStaffMembershipRepository,
    FakeUserDirectory,
    RecordingEventPublisher,
    SequenceUuidGenerator,
    a_staff_invitation,
)


def _seeded_org(repo: FakeOrganizationRepository) -> Organization:
    org, _ = Organization.seed(
        organization_id=OrganizationId.generate(),
        name=OrganizationName("Взлёт талантов"),
        slug=OrganizationSlug("vzlyot-talantov"),
        now=NOW,
    )
    return repo.seed(org)


def _new_user_uuid() -> StaffUserId:
    return StaffUserId.from_uuid(SequenceUuidGenerator().new())


def _active_owner(members: FakeStaffMembershipRepository, org: Organization, user_id: StaffUserId | None = None) -> StaffMembership:
    uid = user_id if user_id is not None else _new_user_uuid()
    membership, _ = StaffMembership.activate_for_owner(
        membership_id=StaffMembershipId.generate(),
        organization_id=org.id,
        user_id=uid,
        now=NOW,
    )
    members.save(membership)
    return membership


def _active_member(
    members: FakeStaffMembershipRepository,
    org: Organization,
    role: StaffRole,
    user_id: StaffUserId | None = None,
) -> StaffMembership:
    uid = user_id if user_id is not None else _new_user_uuid()
    membership = StaffMembership.pending_from_invitation(
        membership_id=StaffMembershipId.generate(),
        organization_id=org.id,
        user_id=uid,
        role=role,
        invited_by=uid,
        invited_at=NOW,
        now=NOW,
    )
    membership.activate(accepted_by=uid, now=NOW)
    members.save(membership)
    return membership


# ---------------------------------------------------------------------------
# Invitation roster & revocation
# ---------------------------------------------------------------------------


class TestListStaffInvitationsHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        members: FakeStaffMembershipRepository,
        invitations: FakeStaffInvitationRepository,
    ) -> ListStaffInvitationsHandler:
        return ListStaffInvitationsHandler(organizations=orgs, memberships=members, invitations=invitations, clock=FakeClock())

    def test_lists_with_derived_status(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)

        pending = a_staff_invitation(organization_id=org.id, email=StaffEmail("pending@example.com"))
        expired = a_staff_invitation(
            organization_id=org.id,
            email=StaffEmail("expired@example.com"),
            expires_at=NOW.replace(year=NOW.year - 1),
        )
        invitations.save(pending)
        invitations.save(expired)

        views = self._handler(orgs, members, invitations).handle(ListStaffInvitationsQuery(requested_by=owner.user_id.json()))

        by_email = {v.email: v for v in views}
        assert by_email["pending@example.com"].status == "pending"
        assert by_email["expired@example.com"].status == "expired"

    def test_rejects_a_caller_who_is_staff_of_no_organization(self) -> None:
        # The roster is scoped to the caller's own organization, so "staff of
        # nowhere" is refused rather than quietly falling back to the first
        # organization on the platform.
        with pytest.raises(PermissionDeniedError):
            self._handler(FakeOrganizationRepository(), FakeStaffMembershipRepository(), FakeStaffInvitationRepository()).handle(
                ListStaffInvitationsQuery(requested_by=_new_user_uuid().json())
            )


class TestRevokeStaffInvitationHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        members: FakeStaffMembershipRepository,
        invitations: FakeStaffInvitationRepository,
        events: RecordingEventPublisher,
    ) -> RevokeStaffInvitationHandler:
        return RevokeStaffInvitationHandler(organizations=orgs, memberships=members, invitations=invitations, clock=FakeClock(), events=events)

    def test_revokes_pending_invitation(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        events = RecordingEventPublisher()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)
        invitation = a_staff_invitation(organization_id=org.id)
        invitations.save(invitation)

        view = self._handler(orgs, members, invitations, events).handle(
            RevokeStaffInvitationCommand(invitation_id=invitation.id.json(), revoked_by=owner.user_id.json())
        )

        assert view.status == "revoked"
        assert invitations.saved[-1].revoked_at is not None
        assert len(events.published) == 1

    def test_unknown_invitation_raises_404(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)
        with pytest.raises(StaffInvitationNotFoundError):
            self._handler(orgs, members, FakeStaffInvitationRepository(), RecordingEventPublisher()).handle(
                RevokeStaffInvitationCommand(invitation_id=StaffMembershipId.generate().json(), revoked_by=owner.user_id.json())
            )

    def test_invitation_from_other_org_raises_404(self) -> None:
        # The whole point of the scoping: another organization's invitation is
        # not visible here at all, let alone revocable.
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)
        foreign = a_staff_invitation(organization_id=OrganizationId.generate())
        invitations.save(foreign)
        with pytest.raises(StaffInvitationNotFoundError):
            self._handler(orgs, members, invitations, RecordingEventPublisher()).handle(
                RevokeStaffInvitationCommand(invitation_id=foreign.id.json(), revoked_by=owner.user_id.json())
            )

    def test_already_revoked_raises_conflict(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        invitations = FakeStaffInvitationRepository()
        events = RecordingEventPublisher()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)
        invitation = a_staff_invitation(organization_id=org.id)
        invitations.save(invitation)
        handler = self._handler(orgs, members, invitations, events)
        handler.handle(RevokeStaffInvitationCommand(invitation_id=invitation.id.json(), revoked_by=owner.user_id.json()))
        with pytest.raises(InvitationStateConflictError):
            handler.handle(RevokeStaffInvitationCommand(invitation_id=invitation.id.json(), revoked_by=owner.user_id.json()))


# ---------------------------------------------------------------------------
# Member roster
# ---------------------------------------------------------------------------


class TestListStaffMembersHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        members: FakeStaffMembershipRepository,
        users: FakeUserDirectory,
    ) -> ListStaffMembersHandler:
        return ListStaffMembersHandler(organizations=orgs, memberships=members, users=users)

    def test_joins_user_cards(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        users = FakeUserDirectory()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)
        users.add(owner.user_id.value, email="owner@example.com", display_name="Пётр Петров")

        views = self._handler(orgs, members, users).handle(ListStaffMembersQuery(requested_by=owner.user_id.json()))

        assert len(views) == 1
        assert views[0].id == owner.id.json()
        assert views[0].email == "owner@example.com"
        assert views[0].display_name == "Пётр Петров"
        assert views[0].role == StaffRole.OWNER.value
        assert views[0].status == "ACTIVE"

    def test_missing_user_card_falls_back_to_none(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)

        views = self._handler(orgs, members, FakeUserDirectory()).handle(ListStaffMembersQuery(requested_by=owner.user_id.json()))

        assert views[0].email is None
        assert views[0].display_name is None


# ---------------------------------------------------------------------------
# Role change (with last-owner guard)
# ---------------------------------------------------------------------------


class TestChangeStaffRoleHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        members: FakeStaffMembershipRepository,
        events: RecordingEventPublisher,
    ) -> ChangeStaffRoleHandler:
        return ChangeStaffRoleHandler(organizations=orgs, memberships=members, clock=FakeClock(), events=events)

    def test_changes_role(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        events = RecordingEventPublisher()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)
        target = _active_member(members, org, StaffRole.SUPPORT)

        view = self._handler(orgs, members, events).handle(
            ChangeStaffRoleCommand(membership_id=target.id.json(), new_role=StaffRole.MODERATOR.value, changed_by=owner.user_id.json())
        )

        assert view.role == StaffRole.MODERATOR.value
        assert members.saved[-1].role is StaffRole.MODERATOR

    def test_promoting_second_owner_then_demoting_first_is_allowed(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        org = _seeded_org(orgs)
        first = _active_owner(members, org)
        second = _active_owner(members, org)  # a second owner exists

        # Demoting the first owner is fine while another active owner remains.
        self._handler(orgs, members, RecordingEventPublisher()).handle(
            ChangeStaffRoleCommand(membership_id=first.id.json(), new_role=StaffRole.DIRECTOR.value, changed_by=second.user_id.json())
        )
        assert members.saved[-1].role is StaffRole.DIRECTOR

    def test_demoting_last_owner_is_refused(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)

        with pytest.raises(LastOwnerError):
            self._handler(orgs, members, RecordingEventPublisher()).handle(
                ChangeStaffRoleCommand(membership_id=owner.id.json(), new_role=StaffRole.DIRECTOR.value, changed_by=owner.user_id.json())
            )

    def test_unknown_membership_raises_404(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)
        with pytest.raises(StaffMembershipNotFoundError):
            self._handler(orgs, members, RecordingEventPublisher()).handle(
                ChangeStaffRoleCommand(
                    membership_id=StaffMembershipId.generate().json(),
                    new_role=StaffRole.SUPPORT.value,
                    changed_by=owner.user_id.json(),
                )
            )


# ---------------------------------------------------------------------------
# Membership revocation (with last-owner guard)
# ---------------------------------------------------------------------------


class TestRevokeStaffMembershipHandler:
    def _handler(
        self,
        orgs: FakeOrganizationRepository,
        members: FakeStaffMembershipRepository,
        events: RecordingEventPublisher,
    ) -> RevokeStaffMembershipHandler:
        return RevokeStaffMembershipHandler(organizations=orgs, memberships=members, clock=FakeClock(), events=events)

    def test_revokes_active_member(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        events = RecordingEventPublisher()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)
        target = _active_member(members, org, StaffRole.SUPPORT)

        view = self._handler(orgs, members, events).handle(
            RevokeStaffMembershipCommand(membership_id=target.id.json(), revoked_by=owner.user_id.json())
        )

        assert view.status == "REVOKED"
        assert members.saved[-1].revoked_at is not None
        assert len(events.published) == 1

    def test_revoking_last_owner_is_refused(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)

        with pytest.raises(LastOwnerError):
            self._handler(orgs, members, RecordingEventPublisher()).handle(
                RevokeStaffMembershipCommand(membership_id=owner.id.json(), revoked_by=owner.user_id.json())
            )

    def test_revoking_already_revoked_raises_conflict(self) -> None:
        orgs = FakeOrganizationRepository()
        members = FakeStaffMembershipRepository()
        org = _seeded_org(orgs)
        owner = _active_owner(members, org)
        target = _active_member(members, org, StaffRole.SUPPORT)
        handler = self._handler(orgs, members, RecordingEventPublisher())
        handler.handle(RevokeStaffMembershipCommand(membership_id=target.id.json(), revoked_by=owner.user_id.json()))
        with pytest.raises(MembershipStateConflictError):
            handler.handle(RevokeStaffMembershipCommand(membership_id=target.id.json(), revoked_by=owner.user_id.json()))
