"""Use cases: competition regulations."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddRegulationCommand,
    MakeRegulationCurrentCommand,
    RemoveRegulationCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.value_objects import (
    FileReference,
    RegulationId,
    RegulationTitle,
    RegulationVersion,
)

from ._support import CompetitionCommandHandler

__all__ = (
    "AddRegulationHandler",
    "MakeRegulationCurrentHandler",
    "RemoveRegulationHandler",
)


class AddRegulationHandler(CompetitionCommandHandler):
    """Publish a new regulation."""

    def handle(
        self,
        command: AddRegulationCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        _, events = competition.add_regulation(
            regulation_id=RegulationId.from_uuid(
                self._uuids.new(),
            ),
            title=RegulationTitle(
                command.title,
            ),
            version=RegulationVersion(
                command.version,
            ),
            publication_date=command.publication_date,
            file=FileReference(
                command.file_reference,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class MakeRegulationCurrentHandler(CompetitionCommandHandler):
    """Mark a regulation as current."""

    def handle(
        self,
        command: MakeRegulationCurrentCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.make_regulation_current(
            regulation_id=RegulationId.from_string(
                command.regulation_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class RemoveRegulationHandler(CompetitionCommandHandler):
    """Remove a regulation."""

    def handle(
        self,
        command: RemoveRegulationCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.remove_regulation(
            regulation_id=RegulationId.from_string(
                command.regulation_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)
