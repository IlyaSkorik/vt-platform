from __future__ import annotations

from apps.organization.application.dto import InvitationView, invitation_status
from apps.organization.application.dto.queries import ListStaffInvitationsQuery
from apps.organization.application.exceptions import OrganizationNotFoundError
from apps.organization.application.interfaces import (
    Clock,
    OrganizationRepository,
    StaffInvitationRepository,
)
from apps.organization.domain.policies import InvitationExpiryPolicy

__all__ = ["ListStaffInvitationsHandler"]


class ListStaffInvitationsHandler:
    """Use case: list every invitation of the singleton organization.

    A read-only roster projection: each invitation is rendered with its
    lifecycle status derived at ``now`` (so a still-open-but-past-window
    invitation reads as ``expired`` without any write).
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        invitations: StaffInvitationRepository,
        clock: Clock,
    ) -> None:
        self._organizations = organizations
        self._invitations = invitations
        self._clock = clock

    def handle(self, query: ListStaffInvitationsQuery) -> list[InvitationView]:
        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("The organization has not been seeded; run migrations first.")

        now = self._clock.utcnow()
        policy = InvitationExpiryPolicy()
        return [
            InvitationView.from_invitation(
                invitation, status=invitation_status(invitation, policy=policy, now=now)
            )
            for invitation in self._invitations.list_by_organization(organization.id)
        ]
