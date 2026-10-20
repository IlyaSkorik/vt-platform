"""Use cases: competition lifecycle."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    CompleteCompetitionCommand,
    LockSubmissionEditingCommand,
    MarkConfiguredCommand,
    MarkReadyCommand,
    PublishCompetitionCommand,
    RevertToConfiguredCommand,
    RevertToDraftCommand,
    StartCompetitionCommand,
    UnlockSubmissionEditingCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.value_objects import CategoryId

from ._support import CompetitionCommandHandler

__all__ = (
    "CompleteCompetitionHandler",
    "LockSubmissionEditingHandler",
    "MarkCompetitionConfiguredHandler",
    "MarkCompetitionReadyHandler",
    "PublishCompetitionHandler",
    "RevertCompetitionToConfiguredHandler",
    "RevertCompetitionToDraftHandler",
    "StartCompetitionHandler",
    "UnlockSubmissionEditingHandler",
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


class LockSubmissionEditingHandler(CompetitionCommandHandler):
    """Freeze everything applicants may still change in one nomination."""

    def handle(self, command: LockSubmissionEditingCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.lock_submission_editing(
            category_id=CategoryId.from_string(command.category_id),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class UnlockSubmissionEditingHandler(CompetitionCommandHandler):
    """Lift one nomination's freeze; its own dates govern again."""

    def handle(self, command: UnlockSubmissionEditingCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.unlock_submission_editing(
            category_id=CategoryId.from_string(command.category_id),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)
