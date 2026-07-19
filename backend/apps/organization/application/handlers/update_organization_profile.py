"""UPDATE organization profile use case."""

from __future__ import annotations

from apps.organization.application.dto.commands import UpdateOrganizationProfileCommand
from apps.organization.application.exceptions import (
    OrganizationNotFoundError,
    translate_domain_errors,
)
from apps.organization.application.handlers.get_organization_profile import OrganizationProfileView
from apps.organization.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationRepository,
)
from apps.organization.domain.value_objects import OrganizationName, OrganizationProfile

__all__ = ["UpdateOrganizationProfileHandler"]


class UpdateOrganizationProfileHandler:
    """Use case: replace the singleton organization's public contact & legal profile.

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
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._organizations = organizations
        self._clock = clock
        self._events = events

    def handle(self, command: UpdateOrganizationProfileCommand) -> OrganizationProfileView:
        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("Organization has not been seeded.")

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
            domain_events = organization.update_profile(profile, name=name, now=self._clock.utcnow())

        self._organizations.save(organization)
        self._events.publish(domain_events)
        return OrganizationProfileView.from_organization(organization)
