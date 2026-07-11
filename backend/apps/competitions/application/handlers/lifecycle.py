"""Use cases: competition lifecycle."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    ArchiveCompetitionCommand,
    CloseRegistrationCommand,
    CompleteCompetitionCommand,
    MarkConfiguredCommand,
    MarkReadyCommand,
    OpenRegistrationCommand,
    PublishCompetitionCommand,
    RevertToConfiguredCommand,
    RevertToDraftCommand,
    StartCompetitionCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView

from ._support import CompetitionCommandHandler

__all__ = (
    "ArchiveCompetitionHandler",
    "CloseRegistrationHandler",
    "CompleteCompetitionHandler",
    "MarkCompetitionConfiguredHandler",
    "MarkCompetitionReadyHandler",
    "OpenRegistrationHandler",
    "PublishCompetitionHandler",
    "RevertCompetitionToConfiguredHandler",
    "RevertCompetitionToDraftHandler",
    "StartCompetitionHandler",
)


class MarkCompetitionConfiguredHandler(CompetitionCommandHandler):
    """Move a competition from DRAFT to CONFIGURED."""

    def handle(
        self,
        command: MarkConfiguredCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.mark_configured(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class RevertCompetitionToDraftHandler(CompetitionCommandHandler):
    """Move a competition from CONFIGURED back to DRAFT."""

    def handle(
        self,
        command: RevertToDraftCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.revert_to_draft(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class MarkCompetitionReadyHandler(CompetitionCommandHandler):
    """Move a competition from CONFIGURED to READY."""

    def handle(
        self,
        command: MarkReadyCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.mark_ready(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class RevertCompetitionToConfiguredHandler(CompetitionCommandHandler):
    """Move a competition from READY back to CONFIGURED."""

    def handle(
        self,
        command: RevertToConfiguredCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.revert_to_configured(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class PublishCompetitionHandler(CompetitionCommandHandler):
    """Publish a competition."""

    def handle(
        self,
        command: PublishCompetitionCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.publish(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class OpenRegistrationHandler(CompetitionCommandHandler):
    """Open competition registration."""

    def handle(
        self,
        command: OpenRegistrationCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.open_registration(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class CloseRegistrationHandler(CompetitionCommandHandler):
    """Close competition registration."""

    def handle(
        self,
        command: CloseRegistrationCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.close_registration(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class StartCompetitionHandler(CompetitionCommandHandler):
    """Mark competition as running."""

    def handle(
        self,
        command: StartCompetitionCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.start(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class CompleteCompetitionHandler(CompetitionCommandHandler):
    """Mark competition as completed."""

    def handle(
        self,
        command: CompleteCompetitionCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.complete(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class ArchiveCompetitionHandler(CompetitionCommandHandler):
    """Archive a competition."""

    def handle(
        self,
        command: ArchiveCompetitionCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.archive(
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)
