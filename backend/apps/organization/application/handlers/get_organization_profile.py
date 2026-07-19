"""GET organization profile use case."""

from __future__ import annotations

from dataclasses import dataclass

from apps.organization.application.exceptions import OrganizationNotFoundError
from apps.organization.application.interfaces import OrganizationRepository
from apps.organization.domain.entities import Organization

__all__ = ["GetOrganizationProfileHandler", "OrganizationProfileView"]


@dataclass(frozen=True, slots=True)
class OrganizationProfileView:
    """Staff-facing, flat read model of the singleton organization's profile."""

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
    """Return the singleton organization profile for staff."""

    def __init__(self, *, organizations: OrganizationRepository) -> None:
        self._organizations = organizations

    def handle(self) -> OrganizationProfileView:
        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("Organization has not been seeded.")
        return OrganizationProfileView.from_organization(organization)
