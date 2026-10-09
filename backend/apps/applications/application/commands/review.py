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
    PromoteWaitlistedSubmissionCommand,
    ReturnSubmissionForCorrectionCommand,
    StartReviewCommand,
    SubmitSubmissionCommand,
    WithdrawCorrectionRequestCommand,
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
    "PromoteWaitlistedSubmissionHandler",
    "ReturnSubmissionForCorrectionHandler",
    "StartReviewHandler",
    "SubmitSubmissionHandler",
    "WithdrawCorrectionRequestHandler",
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

        nomination_id = submission.performance.nomination_id if submission.performance is not None else None
        to_waitlist = False
        if not self._catalog.accepts_submissions(competition_id=submission.competition_id, nomination_id=nomination_id, now=now):
            to_waitlist = nomination_id is not None and self._catalog.accepts_waitlist(
                competition_id=submission.competition_id,
                nomination_id=nomination_id,
                now=now,
            )
            if not to_waitlist:
                raise CompetitionClosedError("Приём заявок на этот фестиваль закрыт.")

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
                raise CompetitionCombinationNotFoundError("Такое сочетание жанра, номинации, возраста и формы участия фестиваль не принимает.")
            policy = resolved

        with translate_domain_errors():
            domain_events = submission.waitlist(policy=policy, now=now) if to_waitlist else submission.submit(policy=policy, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class PromoteWaitlistedSubmissionHandler:
    """Use case: move a waitlisted submission into the competition (organizer).

    The one deliberate asymmetry with :class:`SubmitSubmissionHandler`: no check that
    the nomination is open. The whole point of the queue is that it is not, and the
    organizer promoting from it is the person who closed it. What *is* re-checked is
    the combination — an entry can sit on the list for weeks, and a nomination the
    festival has since dropped must not slip in through the back.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        organization: OrganizationReadModel,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._catalog = catalog
        self._organization = organization
        self._clock = clock
        self._events = events

    def handle(self, command: PromoteWaitlistedSubmissionCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        reviewer_id = parse_reviewer_id(command.reviewer_id)
        ensure_reviewer(self._organization, reviewer_id)
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))

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
                raise CompetitionCombinationNotFoundError("Такое сочетание жанра, номинации, возраста и формы участия фестиваль не принимает.")
            policy = resolved

        with translate_domain_errors():
            domain_events = submission.promote_from_waitlist(policy=policy, now=now)
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


class WithdrawCorrectionRequestHandler:
    """Use case: take a returned submission back into the review queue (organizer).

    The undo for :class:`ReturnSubmissionForCorrectionHandler`. Only the organizer can
    perform it, because only the organizer asked for the correction — and because the
    applicant has no move of their own out of ``REQUIRES_CORRECTION`` beyond editing
    the entry, a request sent in error otherwise parks it for the rest of the season.

    The combination is re-resolved for the same reason :class:`PromoteWaitlistedSubmissionHandler`
    does it: a returned entry stays editable, so what goes back into the queue is not
    necessarily what came out of it.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        organization: OrganizationReadModel,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._catalog = catalog
        self._organization = organization
        self._clock = clock
        self._events = events

    def handle(self, command: WithdrawCorrectionRequestCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        reviewer_id = parse_reviewer_id(command.reviewer_id)
        ensure_reviewer(self._organization, reviewer_id)
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))

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
                raise CompetitionCombinationNotFoundError("Такое сочетание жанра, номинации, возраста и формы участия фестиваль не принимает.")
            policy = resolved

        with translate_domain_errors():
            domain_events = submission.withdraw_correction_request(policy=policy, now=now)
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
