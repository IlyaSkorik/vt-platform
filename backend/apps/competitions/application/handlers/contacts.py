"""Use cases: competition contacts (legacy channels + contacts-module config)."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddContactCommand,
    RemoveContactCommand,
    SetPrimaryContactCommand,
    UpdateContactsConfigCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.contacts_configuration import (
    ContactProfileOverride,
    ContactsConfiguration,
    EmergencyContacts,
    TeamContact,
    VenueDetails,
)
from apps.competitions.domain.value_objects import (
    ContactId,
    ContactType,
    ContactValue,
)
from shared.utils.json_values import as_int

from ._support import CompetitionCommandHandler

__all__ = (
    "AddContactHandler",
    "RemoveContactHandler",
    "SetPrimaryContactHandler",
    "UpdateContactsConfigHandler",
)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _contacts_config_from_command(command: UpdateContactsConfigCommand) -> ContactsConfiguration:
    override = command.override if isinstance(command.override, dict) else {}
    emergency = command.emergency if isinstance(command.emergency, dict) else {}
    venue = command.venue_details if isinstance(command.venue_details, dict) else {}

    team: list[TeamContact] = []
    for raw in command.team_contacts:
        sort_order = as_int(raw.get("sort_order"), minimum=0)
        team.append(
            TeamContact(
                id=str(raw["id"]),
                name=str(raw["name"]),
                position=_optional_str(raw.get("position")),
                phone=_optional_str(raw.get("phone")),
                email=_optional_str(raw.get("email")),
                description=_optional_str(raw.get("description")),
                sort_order=sort_order,
            )
        )

    return ContactsConfiguration(
        use_organization_contacts=command.use_organization_contacts,
        override=ContactProfileOverride(
            organization_name=_optional_str(override.get("organization_name")),
            phone=_optional_str(override.get("phone")),
            email=_optional_str(override.get("email")),
            website=_optional_str(override.get("website")),
            address=_optional_str(override.get("address")),
            vk=_optional_str(override.get("vk")),
            instagram=_optional_str(override.get("instagram")),
            telegram=_optional_str(override.get("telegram")),
        ),
        team_contacts=tuple(team),
        emergency=EmergencyContacts(
            phone=_optional_str(emergency.get("phone")),
            email=_optional_str(emergency.get("email")),
            notes=_optional_str(emergency.get("notes")),
        ),
        venue_details=VenueDetails(
            city=_optional_str(venue.get("city")),
            country=_optional_str(venue.get("country")),
            google_maps_url=_optional_str(venue.get("google_maps_url")),
            yandex_maps_url=_optional_str(venue.get("yandex_maps_url")),
            directions=_optional_str(venue.get("directions")),
        ),
    )


class AddContactHandler(CompetitionCommandHandler):
    """Add a competition contact."""

    def handle(
        self,
        command: AddContactCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.add_contact(
            contact_id=ContactId.from_uuid(
                self._uuids.new(),
            ),
            contact_type=ContactType(
                command.contact_type,
            ),
            value=ContactValue(
                command.value,
            ),
            is_primary=command.is_primary,
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class SetPrimaryContactHandler(CompetitionCommandHandler):
    """Set the primary competition contact."""

    def handle(
        self,
        command: SetPrimaryContactCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.set_primary_contact(
            contact_id=ContactId.from_string(
                command.contact_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class RemoveContactHandler(CompetitionCommandHandler):
    """Remove a competition contact."""

    def handle(
        self,
        command: RemoveContactCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.remove_contact(
            contact_id=ContactId.from_string(
                command.contact_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class UpdateContactsConfigHandler(CompetitionCommandHandler):
    """Replace competition contacts-module configuration."""

    def handle(self, command: UpdateContactsConfigCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        events = competition.update_contacts_config(
            config=_contacts_config_from_command(command),
            now=self._clock.utcnow(),
        )
        return self._persist(competition, events)
