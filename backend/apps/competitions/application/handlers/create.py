from __future__ import annotations

from apps.competitions.application.dto.commands import CreateCompetitionCommand
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.entities import Competition
from apps.competitions.domain.value_objects import (
    CompetitionDescription,
    CompetitionId,
    CompetitionTitle,
    OrganizerId,
    Season,
)

from ._support import CompetitionCommandHandler

__all__ = ["CreateCompetitionHandler"]


class CreateCompetitionHandler(CompetitionCommandHandler):
    """Create a new competition."""

    def handle(
        self,
        command: CreateCompetitionCommand,
    ) -> CompetitionDetailView:
        competition, events = Competition.draft(
            competition_id=CompetitionId.from_uuid(self._uuids.new()),
            title=CompetitionTitle(command.title),
            season=Season(command.season),
            organizer_id=OrganizerId.from_string(command.organizer_id),
            now=self._clock.utcnow(),
            description=(CompetitionDescription(command.description) if command.description else None),
        )

        return self._persist(competition, events)
