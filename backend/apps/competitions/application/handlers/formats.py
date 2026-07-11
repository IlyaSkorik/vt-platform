"""Use cases: add / update / remove participation formats."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddParticipationFormatCommand,
    RemoveParticipationFormatCommand,
    UpdateParticipationFormatCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.entities import _SENTINEL
from apps.competitions.domain.value_objects import (
    ParticipationFormatDescription,
    ParticipationFormatId,
    ParticipationFormatName,
)

from ._support import CompetitionCommandHandler

__all__ = (
    "AddParticipationFormatHandler",
    "RemoveParticipationFormatHandler",
    "UpdateParticipationFormatHandler",
)


class AddParticipationFormatHandler(CompetitionCommandHandler):
    """Add a participation format to a competition."""

    def handle(
        self,
        command: AddParticipationFormatCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        description = None
        if command.description is not None and command.description.strip():
            description = ParticipationFormatDescription(command.description)

        events = competition.add_participation_format(
            format_id=ParticipationFormatId.from_uuid(self._uuids.new()),
            name=ParticipationFormatName(command.name),
            now=self._clock.utcnow(),
            description=description,
            enabled=command.enabled,
            sort_order=command.sort_order,
        )

        return self._persist(competition, events)


class UpdateParticipationFormatHandler(CompetitionCommandHandler):
    """Partial update of a participation format."""

    def handle(
        self,
        command: UpdateParticipationFormatCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        description: object = _SENTINEL
        if command.update_description:
            description = (
                ParticipationFormatDescription(command.description)
                if command.description is not None and command.description.strip()
                else None
            )

        events = competition.update_participation_format(
            format_id=ParticipationFormatId.from_string(command.format_id),
            name=ParticipationFormatName(command.name) if command.name is not None else None,
            description=description,  # type: ignore[arg-type]
            enabled=command.enabled,
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class RemoveParticipationFormatHandler(CompetitionCommandHandler):
    """Hard-remove a participation format."""

    def handle(
        self,
        command: RemoveParticipationFormatCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.remove_participation_format(
            format_id=ParticipationFormatId.from_string(command.format_id),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)
