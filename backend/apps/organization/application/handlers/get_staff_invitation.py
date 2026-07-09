from __future__ import annotations

from apps.organization.application.dto import StaffInvitationDetailsDto
from apps.organization.application.dto.queries import GetStaffInvitationQuery
from apps.organization.application.exceptions import (
    InvalidInvitationTokenError,
    InvitationConflictError,
    OrganizationNotFoundError,
    StaffInvitationNotFoundError,
)
from apps.organization.application.interfaces import (
    Clock,
    OrganizationRepository,
    StaffInvitationRepository,
    TokenHasher,
)
from apps.organization.domain.policies import InvitationExpiryPolicy

__all__ = ["GetStaffInvitationHandler"]


class GetStaffInvitationHandler:
    """Use case: look up a staff invitation by its raw token."""

    def __init__(
        self,
        *,
        invitations: StaffInvitationRepository,
        organizations: OrganizationRepository,
        hasher: TokenHasher,
        clock: Clock,
    ) -> None:
        self._invitations = invitations
        self._organizations = organizations
        self._hasher = hasher
        self._clock = clock

    def handle(self, query: GetStaffInvitationQuery) -> StaffInvitationDetailsDto:
        token_hash = self._hasher.hash(query.raw_token)
        invitation = self._invitations.get_by_token_hash(token_hash)

        if invitation is None:
            raise StaffInvitationNotFoundError("The invitation was not found.")

        if invitation.accepted_at is not None:
            raise InvitationConflictError("The invitation has already been accepted.")

        if invitation.is_expired(policy=InvitationExpiryPolicy(), now=self._clock.utcnow()):
            # I will need to find a better exception for this to map to 410.
            # For now, I will use InvalidInvitationTokenError.
            raise InvalidInvitationTokenError("The invitation has expired.")

        organization = self._organizations.get(invitation.organization_id)
        if organization is None:
            raise OrganizationNotFoundError("The organization was not found.")

        return StaffInvitationDetailsDto(
            organization_name=organization.name.value,
            role=invitation.role.value,
            expires_at=invitation.expires_at,
            invited_email=invitation.email.value,
        )
