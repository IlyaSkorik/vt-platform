"""Use cases: competition contacts."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddContactCommand,
    RemoveContactCommand,
    SetPrimaryContactCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.value_objects import (
    ContactId,
    ContactType,
    ContactValue,
)

from ._support import CompetitionCommandHandler

__all__ = (
    "AddContactHandler",
    "SetPrimaryContactHandler",
    "RemoveContactHandler",
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