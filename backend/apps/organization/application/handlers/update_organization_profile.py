"""UPDATE organization profile use case."""

from __future__ import annotations

from apps.organization.application.dto.commands import UpdateOrganizationProfileCommand
from apps.organization.application.exceptions import translate_domain_errors
from apps.organization.application.handlers._scope import organization_of_actor
from apps.organization.application.handlers.get_organization_profile import OrganizationProfileView
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationRepository,
    StaffMembershipRepository,
)
from apps.organization.domain.value_objects import (
    OrganizationName,
    OrganizationProfile,
    StaffUserId,
    SupportingOrganization,
)

__all__ = ["UpdateOrganizationProfileHandler"]


class UpdateOrganizationProfileHandler:
    """Use case: replace the acting staff member's organization's contact & legal profile.

    A full-replacement edit driven by the staff profile form. Builds the
    :class:`OrganizationProfile` value object (translating any validation error
    into an application error), asks the aggregate to apply it, persists honouring
    the aggregate's version, and publishes whatever events resulted (none when the
    submitted profile is unchanged). Returns the refreshed read model.
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

    def handle(self, command: UpdateOrganizationProfileCommand) -> OrganizationProfileView:
        with translate_domain_errors():
            updated_by = StaffUserId.from_string(command.updated_by)

        # The staff member edits their own organization's profile — resolved from
        # their membership, never a platform-wide default.
        organization, _ = organization_of_actor(
            updated_by,
            organizations=self._organizations,
            memberships=self._memberships,
        )

        with translate_domain_errors():
            name = OrganizationName(command.name) if command.name is not None else None
            profile = OrganizationProfile(
                phone=command.phone,
                email=command.email,
                website=command.website,
                address=command.address,
                logo=command.logo,
                vk=command.vk,
                instagram=command.instagram,
                telegram=command.telegram,
                legal_information=command.legal_information,
            )
            supporter = _supporter_of(command)
            domain_events = organization.update_profile(profile, name=name, supporter=supporter, now=self._clock.utcnow())

        self._organizations.save(organization)
        self._events.publish(domain_events)
        return OrganizationProfileView.from_organization(organization)


def _supporter_of(command: UpdateOrganizationProfileCommand) -> SupportingOrganization | None:
    """Build the supporting entity the command carries, or ``None`` when it names none.

    Two ways to arrive at "no supporting entity" and both mean the same thing: the
    block is absent from the request altogether, or it is present with the name
    cleared. Neither is an error — an organization that does its own work is the
    ordinary case, and clearing the block is how the organizer says so.
    """
    if command.supporter is None:
        return None
    supporter = command.supporter
    return SupportingOrganization.of(
        name=supporter.name,
        phone=supporter.phone,
        email=supporter.email,
        website=supporter.website,
        address=supporter.address,
        vk=supporter.vk,
        instagram=supporter.instagram,
        telegram=supporter.telegram,
        legal_information=supporter.legal_information,
    )
