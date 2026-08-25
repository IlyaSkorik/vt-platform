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
from apps.organization.domain.value_objects import StaffUserId, SupportingOrganization

__all__ = ["GetOrganizationProfileHandler", "OrganizationProfileView", "SupportingOrganizationView"]


@dataclass(frozen=True, slots=True)
class SupportingOrganizationView:
    """Staff-facing read model of the "with the support of" block."""

    name: str
    phone: str | None
    email: str | None
    website: str | None
    address: str | None
    vk: str | None
    instagram: str | None
    telegram: str | None
    legal_information: str | None

    @classmethod
    def of(cls, supporter: SupportingOrganization | None) -> SupportingOrganizationView | None:
        """Project the aggregate's supporting entity, or ``None`` when it has none."""
        if supporter is None:
            return None
        return cls(
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


@dataclass(frozen=True, slots=True)
class OrganizationProfileView:
    """Staff-facing, flat read model of one organization's profile.

    Flat but for ``supporter``: the supporting entity is nested because it is
    present or absent as a whole, and the form needs to tell "no supporting entity"
    from "one whose fields are all blank".
    """

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
    supporter: SupportingOrganizationView | None

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
            supporter=SupportingOrganizationView.of(organization.supporter),
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
