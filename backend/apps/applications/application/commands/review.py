"""Submission & review-lifecycle use cases.

The applicant submits (:class:`SubmitSubmissionHandler`); an authorized organizer
then drives the review: begin it, and either return it for correction or approve
it. Each lifecycle transition is one domain call - the domain owns the legality of
every move.
"""

from __future__ import annotations

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    ApproveSubmissionCommand,
    ReturnSubmissionForCorrectionCommand,
    StartReviewCommand,
    SubmitSubmissionCommand,
)
from apps.applications.application.exceptions import (
    CompetitionClosedError,
    CompetitionCombinationNotFoundError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    Clock,
    CompetitionCatalog,
    EventPublisher,
    OrganizationReadModel,
    SubmissionRepository,
    UuidGenerator,
)
from apps.applications.domain.value_objects import (
    ParticipantCountRange,
    ReviewComment,
    ReviewId,
    SubmissionParticipationPolicy,
)

from ._support import (
    ensure_owner,
    ensure_reviewer,
    load_submission,
    parse_reviewer_id,
    parse_submission_id,
    parse_user_id,
)

__all__ = [
    "ApproveSubmissionHandler",
    "ReturnSubmissionForCorrectionHandler",
    "StartReviewHandler",
    "SubmitSubmissionHandler",
]

#: A placeholder policy used only when a submission has no performance yet. The
#: domain checks "a performance exists" *before* admissibility in
#: ``Submission.submit``, so this stand-in is never actually consulted - it merely
#: lets the domain raise the authoritative ``PerformanceRequiredError``.
_UNRESOLVED_POLICY = SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(min_count=1), is_admissible=False)


class SubmitSubmissionHandler:
    """Use case: submit the submission to its competition (owner).

    Confirms the competition still accepts submissions, resolves the participation
    policy for the performance's combination through the Competition ACL, and hands
    it to the domain, which enforces every submission invariant (performance,
    participants, frozen price, admissibility, participant count).
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock
        self._events = events

    def handle(self, command: SubmitSubmissionCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))

        if not self._catalog.accepts_submissions(
            competition_id=submission.competition_id,
            nomination_id=submission.performance.nomination_id if submission.performance is not None else None,
            now=now,
        ):
            raise CompetitionClosedError("This competition is not currently accepting submissions.")

        performance = submission.performance
        if performance is None:
            policy = _UNRESOLVED_POLICY
        else:
            resolved = self._catalog.participation_policy(
                competition_id=submission.competition_id,
                nomination_id=performance.nomination_id,
                discipline_id=performance.discipline_id,
                age_category_id=performance.age_category_id,
                participant_group_id=performance.participant_group_id,
                participation_format_id=performance.participation_format_id,
            )
            if resolved is None:
                raise CompetitionCombinationNotFoundError("The competition has no configuration for this combination.")
            policy = resolved

        with translate_domain_errors():
            domain_events = submission.submit(policy=policy, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class StartReviewHandler:
    """Use case: begin reviewing a submitted submission (organizer)."""

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

    def handle(self, command: StartReviewCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        reviewer_id = parse_reviewer_id(command.reviewer_id)
        ensure_reviewer(self._organization, reviewer_id)
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        with translate_domain_errors():
            domain_events = submission.begin_review(now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class ReturnSubmissionForCorrectionHandler:
    """Use case: return the submission to the applicant for correction (organizer).

    The review comment is mandatory - the domain records the review that explains
    what to fix as part of the transition.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._organization = organization
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: ReturnSubmissionForCorrectionCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        reviewer_id = parse_reviewer_id(command.reviewer_id)
        ensure_reviewer(self._organization, reviewer_id)
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        review_id = ReviewId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            comment = ReviewComment(command.comment)
            domain_events = submission.return_for_correction(
                review_id=review_id,
                reviewer_id=reviewer_id,
                comment=comment,
                now=now,
            )
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class ApproveSubmissionHandler:
    """Use case: approve the submission under review (organizer)."""

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

    def handle(self, command: ApproveSubmissionCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        reviewer_id = parse_reviewer_id(command.reviewer_id)
        ensure_reviewer(self._organization, reviewer_id)
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        with translate_domain_errors():
            domain_events = submission.approve(now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
