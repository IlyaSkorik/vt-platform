"""GET organization profile use case."""

from __future__ import annotations

from dataclasses import dataclass

from apps.organization.application.dto.queries import GetOrganizationProfileQuery
from apps.organization.application.handlers._scope import organization_of_actor
from apps.organization.application.interfaces import (
    OrganizationRepository,
    StaffMembershipRepository,
)
from apps.organization.domain.entities import Organization
from apps.organization.domain.value_objects import StaffUserId

__all__ = ["GetOrganizationProfileHandler", "OrganizationProfileView"]


@dataclass(frozen=True, slots=True)
class OrganizationProfileView:
    """Staff-facing, flat read model of one organization's profile."""

    id: str
    name: str
    slug: str
    phone: str | None
    email: str | None
    website: str | None
    address: str | None
    logo: str | None
    vk: str | None
    instagram: str | None
    telegram: str | None
    legal_information: str | None

    @classmethod
    def from_organization(cls, organization: Organization) -> OrganizationProfileView:
        """Flatten an :class:`Organization` aggregate into its profile read model."""
        profile = organization.profile
        return cls(
            id=organization.id.json(),
            name=organization.name.value,
            slug=organization.slug.value,
            phone=profile.phone,
            email=profile.email,
            website=profile.website,
            address=profile.address,
            logo=profile.logo,
            vk=profile.vk,
            instagram=profile.instagram,
            telegram=profile.telegram,
            legal_information=profile.legal_information,
        )


class GetOrganizationProfileHandler:
    """Return the caller's own organization profile.

    Which organization that is comes from the caller's staff membership: with
    several connected to the platform, "the organization" is only ever the one the
    reader belongs to.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: StaffMembershipRepository,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships

    def handle(self, query: GetOrganizationProfileQuery) -> OrganizationProfileView:
        organization, _ = organization_of_actor(
            StaffUserId.from_string(query.requested_by),
            organizations=self._organizations,
            memberships=self._memberships,
        )
        return OrganizationProfileView.from_organization(organization)
