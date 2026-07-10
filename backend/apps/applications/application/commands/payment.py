"""Payment & acceptance lifecycle use cases (organizer-driven)."""

from __future__ import annotations

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    AcceptSubmissionCommand,
    MarkPaidCommand,
    MarkWaitingPaymentCommand,
)
from apps.applications.application.exceptions import translate_domain_errors
from apps.applications.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationReadModel,
    SubmissionRepository,
)

from ._support import ensure_reviewer, load_submission, parse_reviewer_id, parse_submission_id

__all__ = ["AcceptSubmissionHandler", "MarkPaidHandler", "MarkWaitingPaymentHandler"]


class MarkWaitingPaymentHandler:
    """Use case: move the approved submission to awaiting payment (organizer)."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._organization = organization
        self._clock = clock
        self._events = events

    def handle(self, command: MarkWaitingPaymentCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        reviewer_id = parse_reviewer_id(command.reviewer_id)
        ensure_reviewer(self._organization, reviewer_id)
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        with translate_domain_errors():
            domain_events = submission.await_payment(now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class MarkPaidHandler:
    """Use case: mark the submission's fee as paid (organizer)."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._organization = organization
        self._clock = clock
        self._events = events

    def handle(self, command: MarkPaidCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        reviewer_id = parse_reviewer_id(command.reviewer_id)
        ensure_reviewer(self._organization, reviewer_id)
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        with translate_domain_errors():
            domain_events = submission.mark_paid(now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class AcceptSubmissionHandler:
    """Use case: accept the paid submission into the competition (organizer).

    From here the domain freezes the submission's content permanently.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._organization = organization
        self._clock = clock
        self._events = events

    def handle(self, command: AcceptSubmissionCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        reviewer_id = parse_reviewer_id(command.reviewer_id)
        ensure_reviewer(self._organization, reviewer_id)
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        with translate_domain_errors():
            domain_events = submission.accept(now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
