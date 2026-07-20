from __future__ import annotations

from apps.organization.application.dto import StaffMembershipView
from apps.organization.application.dto.commands import RevokeStaffMembershipCommand
from apps.organization.application.exceptions import (
    LastOwnerError,
    OrganizationNotFoundError,
    StaffMembershipNotFoundError,
    translate_domain_errors,
)
from apps.organization.application.handlers._staff_guards import is_sole_active_owner
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationRepository,
    StaffMembershipRepository,
)
from apps.organization.domain.value_objects import StaffMembershipId, StaffUserId

__all__ = ["RevokeStaffMembershipHandler"]


class RevokeStaffMembershipHandler:
    """Use case: revoke an active staff membership, removing staff access.

    Authorization (only OWNER/DIRECTOR) is enforced at the presentation edge. The
    handler guards that the membership belongs to the singleton organization and
    refuses to revoke the last active OWNER (:class:`LastOwnerError`). Revoking an
    already-revoked membership raises through :func:`translate_domain_errors`.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: StaffMembershipRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._clock = clock
        self._events = events

    def handle(self, command: RevokeStaffMembershipCommand) -> StaffMembershipView:
        now = self._clock.utcnow()

        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("The organization has not been seeded; run migrations first.")

        with translate_domain_errors():
            membership_id = StaffMembershipId.from_string(command.membership_id)
            revoked_by = StaffUserId.from_string(command.revoked_by)

        membership = self._memberships.get(membership_id)
        if (
            membership is None
            or membership.deleted_at is not None
            or membership.organization_id != organization.id
        ):
            raise StaffMembershipNotFoundError("The staff membership was not found.")

        if is_sole_active_owner(self._memberships.list_by_organization(organization.id), membership):
            raise LastOwnerError("The last active owner cannot be revoked.")

        with translate_domain_errors():
            events = membership.revoke(revoked_by=revoked_by, now=now)

        self._memberships.save(membership)
        self._events.publish(events)
        return StaffMembershipView.from_membership(membership)
