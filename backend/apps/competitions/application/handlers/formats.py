"""Use cases: enable / disable participation formats."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    DisableFormatCommand,
    EnableFormatCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.value_objects import ParticipationFormat

from ._support import CompetitionCommandHandler

__all__ = (
    "DisableFormatHandler",
    "EnableFormatHandler",
)


class EnableFormatHandler(CompetitionCommandHandler):
    """Enable a participation format for a competition."""

    def handle(
        self,
        command: EnableFormatCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.enable_format(
            participation_format=ParticipationFormat(
                command.participation_format,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class DisableFormatHandler(CompetitionCommandHandler):
    """Disable a participation format."""

    def handle(
        self,
        command: DisableFormatCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.disable_format(
            participation_format=ParticipationFormat(
                command.participation_format,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)
