from __future__ import annotations

from apps.organization.application.dto import (
    MembershipOperationResultDto,
    StaffMembershipView,
)
from apps.organization.application.dto.commands import AcceptStaffInvitationCommand
from apps.organization.application.exceptions import (
    InvalidInvitationTokenError,
    OrganizationNotFoundError,
    PermissionDeniedError,
    UserAlreadyStaffError,
    translate_domain_errors,
)
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationRepository,
    StaffInvitationRepository,
    StaffMembershipRepository,
    TokenHasher,
    UuidGenerator,
)
from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.policies import InvitationExpiryPolicy
from apps.organization.domain.value_objects import (
    StaffEmail,
    StaffMembershipId,
    StaffUserId,
)

__all__ = ["AcceptStaffInvitationHandler"]


class AcceptStaffInvitationHandler:
    """Use case: accept a staff invitation and create the staff membership."""

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: StaffMembershipRepository,
        invitations: StaffInvitationRepository,
        clock: Clock,
        uuids: UuidGenerator,
        hasher: TokenHasher,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._invitations = invitations
        self._clock = clock
        self._uuids = uuids
        self._hasher = hasher
        self._events = events

    def handle(self, command: AcceptStaffInvitationCommand) -> MembershipOperationResultDto:
        now = self._clock.utcnow()

        with translate_domain_errors():
            accepted_by = StaffUserId.from_string(command.accepted_by)
            email = StaffEmail(command.email)

        token_hash = self._hasher.hash(command.raw_token)
        invitation = self._invitations.get_by_token_hash(token_hash)
        if invitation is None:
            raise InvalidInvitationTokenError("The invitation token is invalid or has expired.")

        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("The organization has not been seeded; run migrations first.")

        if invitation.email != email:
            raise PermissionDeniedError("This invitation is not for the authenticated user.")

        if self._memberships.exists_active(user_id=accepted_by, organization_id=organization.id):
            raise UserAlreadyStaffError("This user already has an active staff membership.")

        with translate_domain_errors():
            invitation_events = invitation.accept(
                accepted_by=accepted_by,
                policy=InvitationExpiryPolicy(),
                now=now,
            )

        membership_id = StaffMembershipId.from_uuid(self._uuids.new())
        membership = StaffMembership.pending_from_invitation(
            membership_id=membership_id,
            organization_id=organization.id,
            user_id=accepted_by,
            role=invitation.role,
            invited_by=invitation.invited_by,
            invited_at=now,
            now=now,
        )
        membership_events = membership.activate(accepted_by=accepted_by, now=now)

        self._invitations.save(invitation)
        self._memberships.save(membership)
        self._events.publish(tuple(invitation_events + membership_events))
        return MembershipOperationResultDto(
            membership=StaffMembershipView.from_membership(membership),
            events=tuple(invitation_events + membership_events),
        )
