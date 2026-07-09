from __future__ import annotations

from apps.organization.application.dto import (
    MembershipOperationResultDto,
    StaffMembershipView,
)
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.application.exceptions import (
    OrganizationNotFoundError,
    UserAlreadyStaffError,
    translate_domain_errors,
)
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationRepository,
    StaffMembershipRepository,
    UuidGenerator,
)
from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.value_objects import (
    StaffMembershipId,
    StaffUserId,
)

__all__ = ["ProvisionOwnerHandler"]


class ProvisionOwnerHandler:
    """Use case: provision the first OWNER membership for an existing user.

    The sanctioned break-glass behind ``manage.py bootstrap_owner`` — the only way
    to create staff without an invitation, run once per environment. It is
    idempotent-friendly: if the user already has an active membership it refuses
    with :class:`UserAlreadyStaffError` rather than creating a duplicate. Events
    are published here (the command is itself the trigger, not an aggregate
    mutation returned to a caller).
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: StaffMembershipRepository,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: ProvisionOwnerCommand) -> MembershipOperationResultDto:
        now = self._clock.utcnow()
        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("The organization has not been seeded; run migrations first.")
        with translate_domain_errors():
            user_id = StaffUserId.from_string(command.user_id)

        if self._memberships.exists_active(user_id=user_id, organization_id=organization.id):
            raise UserAlreadyStaffError("This user already has an active staff membership.")

        membership_id = StaffMembershipId.from_uuid(self._uuids.new())
        membership, domain_events = StaffMembership.activate_for_owner(
            membership_id=membership_id,
            organization_id=organization.id,
            user_id=user_id,
            now=now,
        )
        self._memberships.save(membership)
        self._events.publish(domain_events)
        return MembershipOperationResultDto(
            membership=StaffMembershipView.from_membership(membership),
            events=tuple(domain_events),
        )
