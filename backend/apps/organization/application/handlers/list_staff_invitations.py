from __future__ import annotations

from apps.organization.application.dto import InvitationView, invitation_status
from apps.organization.application.dto.queries import ListStaffInvitationsQuery
from apps.organization.application.handlers._scope import organization_of_actor
from apps.organization.application.interfaces import (
    Clock,
    OrganizationRepository,
    StaffInvitationRepository,
    StaffMembershipRepository,
)
from apps.organization.domain.policies import InvitationExpiryPolicy
from apps.organization.domain.value_objects import StaffUserId

__all__ = ["ListStaffInvitationsHandler"]


class ListStaffInvitationsHandler:
    """Use case: list every invitation of the caller's own organization.

    A read-only roster projection: each invitation is rendered with its
    lifecycle status derived at ``now`` (so a still-open-but-past-window
    invitation reads as ``expired`` without any write).
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: StaffMembershipRepository,
        invitations: StaffInvitationRepository,
        clock: Clock,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._invitations = invitations
        self._clock = clock

    def handle(self, query: ListStaffInvitationsQuery) -> list[InvitationView]:
        organization, _ = organization_of_actor(
            StaffUserId.from_string(query.requested_by),
            organizations=self._organizations,
            memberships=self._memberships,
        )

        now = self._clock.utcnow()
        policy = InvitationExpiryPolicy()
        return [
            InvitationView.from_invitation(invitation, status=invitation_status(invitation, policy=policy, now=now))
            for invitation in self._invitations.list_by_organization(organization.id)
        ]
