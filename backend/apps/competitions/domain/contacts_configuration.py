"""Contacts configuration value objects for a competition.

Separate from the legacy channel :class:`~apps.competitions.domain.entities.Contact`
(PHONE/EMAIL/VK) children. This bag drives the public contacts module: org profile
reuse, optional overrides, team people, emergency lines, and venue map details.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace

from .exceptions import InvalidContactsConfigurationError

__all__ = [
    "ContactProfileOverride",
    "ContactsConfiguration",
    "EmergencyContacts",
    "TeamContact",
    "VenueDetails",
]


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


@dataclass(frozen=True, slots=True)
class ContactProfileOverride:
    """Optional per-competition overrides of organization contact fields."""

    organization_name: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    vk: str | None = None
    instagram: str | None = None
    telegram: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "organization_name", _optional_str(self.organization_name))
        object.__setattr__(self, "phone", _optional_str(self.phone))
        object.__setattr__(self, "email", _optional_str(self.email))
        object.__setattr__(self, "website", _optional_str(self.website))
        object.__setattr__(self, "address", _optional_str(self.address))
        object.__setattr__(self, "vk", _optional_str(self.vk))
        object.__setattr__(self, "instagram", _optional_str(self.instagram))
        object.__setattr__(self, "telegram", _optional_str(self.telegram))

    @classmethod
    def empty(cls) -> ContactProfileOverride:
        return cls()


@dataclass(frozen=True, slots=True)
class TeamContact:
    """A named team member shown on the competition contacts page."""

    id: str
    name: str
    position: str | None = None
    phone: str | None = None
    email: str | None = None
    description: str | None = None
    sort_order: int = 0

    def __post_init__(self) -> None:
        try:
            uuid.UUID(str(self.id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise InvalidContactsConfigurationError("Team contact id must be a valid UUID.") from exc
        name = (self.name or "").strip()
        if not name:
            raise InvalidContactsConfigurationError("Team contact name must not be empty.")
        if self.sort_order < 0:
            raise InvalidContactsConfigurationError("Team contact sort order must be non-negative.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "position", _optional_str(self.position))
        object.__setattr__(self, "phone", _optional_str(self.phone))
        object.__setattr__(self, "email", _optional_str(self.email))
        object.__setattr__(self, "description", _optional_str(self.description))


@dataclass(frozen=True, slots=True)
class EmergencyContacts:
    """Optional emergency phone/email and free-form notes."""

    phone: str | None = None
    email: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "phone", _optional_str(self.phone))
        object.__setattr__(self, "email", _optional_str(self.email))
        object.__setattr__(self, "notes", _optional_str(self.notes))

    @classmethod
    def empty(cls) -> EmergencyContacts:
        return cls()


@dataclass(frozen=True, slots=True)
class VenueDetails:
    """Optional venue location and directions beyond the competition venue name."""

    city: str | None = None
    country: str | None = None
    google_maps_url: str | None = None
    yandex_maps_url: str | None = None
    directions: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "city", _optional_str(self.city))
        object.__setattr__(self, "country", _optional_str(self.country))
        object.__setattr__(self, "google_maps_url", _optional_str(self.google_maps_url))
        object.__setattr__(self, "yandex_maps_url", _optional_str(self.yandex_maps_url))
        object.__setattr__(self, "directions", _optional_str(self.directions))

    @classmethod
    def empty(cls) -> VenueDetails:
        return cls()


@dataclass(frozen=True, slots=True)
class ContactsConfiguration:
    """Immutable contacts-module configuration for a competition."""

    use_organization_contacts: bool = True
    override: ContactProfileOverride = field(default_factory=ContactProfileOverride.empty)
    team_contacts: tuple[TeamContact, ...] = ()
    emergency: EmergencyContacts = field(default_factory=EmergencyContacts.empty)
    venue_details: VenueDetails = field(default_factory=VenueDetails.empty)

    def __post_init__(self) -> None:
        if not isinstance(self.override, ContactProfileOverride):
            raise InvalidContactsConfigurationError("Override must be a ContactProfileOverride.")
        if not isinstance(self.emergency, EmergencyContacts):
            raise InvalidContactsConfigurationError("Emergency must be an EmergencyContacts.")
        if not isinstance(self.venue_details, VenueDetails):
            raise InvalidContactsConfigurationError("Venue details must be a VenueDetails.")
        seen: set[str] = set()
        for item in self.team_contacts:
            if not isinstance(item, TeamContact):
                raise InvalidContactsConfigurationError("Team contacts must be TeamContact values.")
            if item.id in seen:
                raise InvalidContactsConfigurationError("Duplicate team contact id.")
            seen.add(item.id)

    @classmethod
    def default(cls) -> ContactsConfiguration:
        """The default contacts configuration a competition starts with."""
        return cls()

    def with_changes(self, **changes: object) -> ContactsConfiguration:
        """A copy with the given fields overridden (rejects unknown names)."""
        return replace(self, **changes)
