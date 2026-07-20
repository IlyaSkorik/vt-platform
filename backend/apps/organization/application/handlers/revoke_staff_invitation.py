from __future__ import annotations

from apps.organization.application.dto import InvitationView
from apps.organization.application.dto.commands import RevokeStaffInvitationCommand
from apps.organization.application.exceptions import (
    OrganizationNotFoundError,
    StaffInvitationNotFoundError,
    translate_domain_errors,
)
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationRepository,
    StaffInvitationRepository,
)
from apps.organization.domain.value_objects import StaffInvitationId, StaffUserId

__all__ = ["RevokeStaffInvitationHandler"]


class RevokeStaffInvitationHandler:
    """Use case: revoke a still-pending staff invitation.

    Authorization (only OWNER/DIRECTOR) is enforced at the presentation edge; the
    handler guards that the invitation belongs to the singleton organization and
    that its own state permits revocation (an accepted or already-revoked
    invitation raises through :func:`translate_domain_errors`).
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        invitations: StaffInvitationRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._invitations = invitations
        self._clock = clock
        self._events = events

    def handle(self, command: RevokeStaffInvitationCommand) -> InvitationView:
        now = self._clock.utcnow()

        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("The organization has not been seeded; run migrations first.")

        with translate_domain_errors():
            invitation_id = StaffInvitationId.from_string(command.invitation_id)
            revoked_by = StaffUserId.from_string(command.revoked_by)

        invitation = self._invitations.get(invitation_id)
        if (
            invitation is None
            or invitation.deleted_at is not None
            or invitation.organization_id != organization.id
        ):
            raise StaffInvitationNotFoundError("The invitation was not found.")

        with translate_domain_errors():
            events = invitation.revoke(revoked_by=revoked_by, now=now)

        self._invitations.save(invitation)
        self._events.publish(events)
        return InvitationView.from_invitation(invitation, status="revoked")
