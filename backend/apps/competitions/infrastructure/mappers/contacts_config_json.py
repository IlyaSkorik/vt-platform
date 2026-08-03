"""Contacts-config JSON ACL helpers for the Competition aggregate.

Translates
:class:`~apps.competitions.domain.contacts_configuration.ContactsConfiguration`
to/from the root row's ``contacts_config`` JSON column.
"""

from __future__ import annotations

from apps.competitions.domain.contacts_configuration import (
    ContactProfileOverride,
    ContactsConfiguration,
    EmergencyContacts,
    TeamContact,
    VenueDetails,
)
from shared.utils.json_values import as_int

__all__ = ["contacts_config_from_json", "contacts_config_to_json"]


def contacts_config_to_json(config: ContactsConfiguration) -> dict[str, object]:
    """Serialize contacts configuration for the competitions.contacts_config JSON column."""
    return {
        "use_organization_contacts": config.use_organization_contacts,
        "override": {
            "organization_name": config.override.organization_name,
            "phone": config.override.phone,
            "email": config.override.email,
            "website": config.override.website,
            "address": config.override.address,
            "vk": config.override.vk,
            "instagram": config.override.instagram,
            "telegram": config.override.telegram,
        },
        "team_contacts": [
            {
                "id": item.id,
                "name": item.name,
                "position": item.position,
                "phone": item.phone,
                "email": item.email,
                "description": item.description,
                "sort_order": item.sort_order,
            }
            for item in config.team_contacts
        ],
        "emergency": {
            "phone": config.emergency.phone,
            "email": config.emergency.email,
            "notes": config.emergency.notes,
        },
        "venue_details": {
            "city": config.venue_details.city,
            "country": config.venue_details.country,
            "google_maps_url": config.venue_details.google_maps_url,
            "yandex_maps_url": config.venue_details.yandex_maps_url,
            "directions": config.venue_details.directions,
        },
    }


def contacts_config_from_json(data: object) -> ContactsConfiguration:
    """Rebuild contacts configuration from JSON, falling back to defaults."""
    default = ContactsConfiguration.default()
    if not isinstance(data, dict) or not data:
        return default

    override_raw = data.get("override") if isinstance(data.get("override"), dict) else {}
    assert isinstance(override_raw, dict)
    emergency_raw = data.get("emergency") if isinstance(data.get("emergency"), dict) else {}
    assert isinstance(emergency_raw, dict)
    venue_raw = data.get("venue_details") if isinstance(data.get("venue_details"), dict) else {}
    assert isinstance(venue_raw, dict)

    team_raw = data.get("team_contacts", [])
    team_contacts: list[TeamContact] = []
    if isinstance(team_raw, list):
        for item in team_raw:
            if not isinstance(item, dict):
                continue
            parsed = _team_contact_from_json(item)
            if parsed is not None:
                team_contacts.append(parsed)

    return ContactsConfiguration(
        use_organization_contacts=bool(data.get("use_organization_contacts", default.use_organization_contacts)),
        override=ContactProfileOverride(
            organization_name=_str_or_none(override_raw.get("organization_name")),
            phone=_str_or_none(override_raw.get("phone")),
            email=_str_or_none(override_raw.get("email")),
            website=_str_or_none(override_raw.get("website")),
            address=_str_or_none(override_raw.get("address")),
            vk=_str_or_none(override_raw.get("vk")),
            instagram=_str_or_none(override_raw.get("instagram")),
            telegram=_str_or_none(override_raw.get("telegram")),
        ),
        team_contacts=tuple(team_contacts),
        emergency=EmergencyContacts(
            phone=_str_or_none(emergency_raw.get("phone")),
            email=_str_or_none(emergency_raw.get("email")),
            notes=_str_or_none(emergency_raw.get("notes")),
        ),
        venue_details=VenueDetails(
            city=_str_or_none(venue_raw.get("city")),
            country=_str_or_none(venue_raw.get("country")),
            google_maps_url=_str_or_none(venue_raw.get("google_maps_url")),
            yandex_maps_url=_str_or_none(venue_raw.get("yandex_maps_url")),
            directions=_str_or_none(venue_raw.get("directions")),
        ),
    )


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _team_contact_from_json(data: dict[str, object]) -> TeamContact | None:
    raw_id = data.get("id")
    raw_name = data.get("name")
    if not isinstance(raw_id, str) or not raw_id:
        return None
    if not isinstance(raw_name, str) or not raw_name.strip():
        return None
    sort_order = as_int(data.get("sort_order"), minimum=0)
    try:
        return TeamContact(
            id=raw_id,
            name=raw_name,
            position=_str_or_none(data.get("position")),
            phone=_str_or_none(data.get("phone")),
            email=_str_or_none(data.get("email")),
            description=_str_or_none(data.get("description")),
            sort_order=max(0, sort_order),
        )
    except Exception:
        return None
