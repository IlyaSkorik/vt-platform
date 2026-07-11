"""GET organization profile use case."""

from __future__ import annotations

from dataclasses import dataclass

from apps.organization.application.exceptions import OrganizationNotFoundError
from apps.organization.application.interfaces import OrganizationRepository

__all__ = ["GetOrganizationProfileHandler", "OrganizationProfileView"]


@dataclass(frozen=True, slots=True)
class OrganizationProfileView:
    """Staff-facing organization profile (contact fields stubbed until persisted)."""

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


class GetOrganizationProfileHandler:
    """Return the singleton organization profile for staff."""

    def __init__(self, *, organizations: OrganizationRepository) -> None:
        self._organizations = organizations

    def handle(self) -> OrganizationProfileView:
        organization = self._organizations.get_default()
        if organization is None:
            raise OrganizationNotFoundError("Organization has not been seeded.")
        return OrganizationProfileView(
            id=organization.id.json(),
            name=organization.name.value,
            slug=organization.slug.value,
            phone=None,
            email=None,
            website=None,
            address=None,
            logo=None,
            vk=None,
            instagram=None,
            telegram=None,
            legal_information=None,
        )
