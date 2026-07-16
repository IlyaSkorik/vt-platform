"""Cancellation use case: the applicant withdraws the submission."""

from __future__ import annotations

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import CancelSubmissionByReviewerCommand, CancelSubmissionCommand
from apps.applications.application.exceptions import translate_domain_errors
from apps.applications.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationReadModel,
    SubmissionRepository,
)

from ._support import ensure_owner, ensure_reviewer, load_submission, parse_reviewer_id, parse_submission_id, parse_user_id

__all__ = ["CancelSubmissionByReviewerHandler", "CancelSubmissionHandler"]


class CancelSubmissionHandler:
    """Use case: cancel (withdraw) the submission on the applicant's behalf.

    The domain permits cancellation from any state up to - but not including -
    ACCEPTED, and refuses it thereafter; the use case only enforces ownership.
    Organizer-initiated rejection is a future extension that would authorize a
    reviewer here instead.
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

    def handle(self, command: CancelSubmissionCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        with translate_domain_errors():
            domain_events = submission.cancel(now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class CancelSubmissionByReviewerHandler:
    """Use case: cancel (reject) a submission by organizer decision."""

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

    def handle(self, command: CancelSubmissionByReviewerCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        reviewer_id = parse_reviewer_id(command.reviewer_id)
        ensure_reviewer(self._organization, reviewer_id)
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        with translate_domain_errors():
            domain_events = submission.cancel(now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
