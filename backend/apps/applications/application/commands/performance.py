"""Performance use cases: set or replace a submission's single performance."""

from __future__ import annotations

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    SetPerformanceCommand,
    UpdatePerformanceCommand,
)
from apps.applications.application.exceptions import (
    SubmissionStateConflictError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    Clock,
    EventPublisher,
    SubmissionRepository,
)
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    DisciplineId,
    Duration,
    NominationId,
    ParticipantGroupId,
    ParticipationFormatId,
    Performance,
    PerformanceTitle,
)

from ._support import ensure_owner, load_submission, parse_submission_id, parse_user_id

__all__ = ["SetPerformanceHandler", "UpdatePerformanceHandler"]


def _performance_from(
    *,
    title: str,
    duration_seconds: int,
    nomination_id: str,
    discipline_id: str,
    age_category_id: str,
    participant_group_id: str,
    participation_format_id: str,
) -> Performance:
    """Build the :class:`Performance` value object, translating validation errors."""
    with translate_domain_errors():
        return Performance(
            title=PerformanceTitle(title),
            duration=Duration.of_seconds(duration_seconds),
            nomination_id=NominationId.from_string(nomination_id),
            discipline_id=DisciplineId.from_string(discipline_id),
            age_category_id=AgeCategoryId.from_string(age_category_id),
            participant_group_id=ParticipantGroupId.from_string(participant_group_id),
            participation_format_id=ParticipationFormatId.from_string(participation_format_id),
        )


class SetPerformanceHandler:
    """Use case: set (or replace) the submission's single performance."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._clock = clock
        self._events = events

    def handle(self, command: SetPerformanceCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))

        performance = _performance_from(
            title=command.title,
            duration_seconds=command.duration_seconds,
            nomination_id=command.nomination_id,
            discipline_id=command.discipline_id,
            age_category_id=command.age_category_id,
            participant_group_id=command.participant_group_id,
            participation_format_id=command.participation_format_id,
        )
        with translate_domain_errors():
            domain_events = submission.set_performance(performance=performance, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class UpdatePerformanceHandler:
    """Use case: replace an *existing* performance.

    Distinguished from :class:`SetPerformanceHandler` by requiring that a
    performance is already present; both delegate the actual replacement (and the
    editable-state check) to the domain.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._clock = clock
        self._events = events

    def handle(self, command: UpdatePerformanceCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        if submission.performance is None:
            raise SubmissionStateConflictError(
                "There is no performance to update; set one first.",
                domain_code="performance_not_set",
            )

        performance = _performance_from(
            title=command.title,
            duration_seconds=command.duration_seconds,
            nomination_id=command.nomination_id,
            discipline_id=command.discipline_id,
            age_category_id=command.age_category_id,
            participant_group_id=command.participant_group_id,
            participation_format_id=command.participation_format_id,
        )
        with translate_domain_errors():
            domain_events = submission.set_performance(performance=performance, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
