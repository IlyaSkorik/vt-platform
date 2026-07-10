"""Use case: create a new DRAFT competition."""

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
    """Create a brand-new competition in the DRAFT state."""

    def handle(self, command: CreateCompetitionCommand) -> CompetitionDetailView:
        now = self._clock.utcnow()
        competition, events = Competition.draft(
            competition_id=CompetitionId.from_uuid(self._uuids.new()),
            title=CompetitionTitle(command.title),
            season=Season(command.season),
            organizer_id=OrganizerId.from_string(command.organizer_id),
            now=now,
            description=CompetitionDescription(command.description) if command.description else None,
        )
        return self._persist(competition, events)
