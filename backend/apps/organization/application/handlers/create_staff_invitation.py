from __future__ import annotations

from apps.organization.application.dto import (
    InvitationOperationResultDto,
    InvitationView,
)
from apps.organization.application.dto.commands import InviteStaffCommand
from apps.organization.application.exceptions import (
    InvitationConflictError,
    OrganizationNotFoundError,
    PermissionDeniedError,
)
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    InvitationTokenService,
    OrganizationRepository,
    StaffInvitationRepository,
    StaffMembershipRepository,
    TokenHasher,
    UuidGenerator,
)
from apps.organization.domain.entities import StaffInvitation
from apps.organization.domain.policies import InvitationExpiryPolicy
from apps.organization.domain.value_objects import (
    StaffEmail,
    StaffInvitationId,
    StaffRole,
    StaffUserId,
)

__all__ = ["InviteStaffHandler"]


class InviteStaffHandler:
    """Use case: issue a staff invitation to a user email.

    Only an ACTIVE OWNER may create invitations; the invitation is stored with a
    one-way hash of the raw token and the email link is emitted side-effect free
    via the outbound ports.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: StaffMembershipRepository,
        invitations: StaffInvitationRepository,
        clock: Clock,
        uuids: UuidGenerator,
        hasher: TokenHasher,
        token_service: InvitationTokenService,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._invitations = invitations
        self._clock = clock
        self._uuids = uuids
        self._hasher = hasher
        self._token_service = token_service
        self._events = events

    def handle(self, command: InviteStaffCommand) -> InvitationOperationResultDto:
        now = self._clock.utcnow()
        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("The organization has not been seeded; run migrations first.")

        email = StaffEmail(command.email)
        role = StaffRole(command.role)
        invited_by = StaffUserId.from_string(command.invited_by)

        inviter_membership = self._memberships.find_active(user_id=invited_by, organization_id=organization.id)
        if inviter_membership is None or not inviter_membership.has_role(StaffRole.OWNER, StaffRole.DIRECTOR):
            raise PermissionDeniedError("Only active owners or directors may issue staff invitations.")

        if self._invitations.find_pending_by_email(email=email, organization_id=organization.id) is not None:
            raise InvitationConflictError("An open invitation already exists for this email.")

        issued_token = self._hasher.generate()
        invitation_id = StaffInvitationId.from_uuid(self._uuids.new())
        invitation, domain_events = StaffInvitation.issue(
            invitation_id=invitation_id,
            organization_id=organization.id,
            email=email,
            role=role,
            token_hash=issued_token.token_hash,
            raw_token=issued_token.raw_token,
            invited_by=invited_by,
            policy=InvitationExpiryPolicy(),
            now=now,
        )
        self._invitations.save(invitation)
        self._events.publish(domain_events)
        return InvitationOperationResultDto(
            invitation=InvitationView.from_invitation(invitation),
            raw_token=issued_token.raw_token,
            events=tuple(domain_events),
        )
