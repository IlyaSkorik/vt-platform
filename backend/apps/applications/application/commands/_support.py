"""Shared orchestration helpers for the Applications command use cases.

Thin, framework-free helpers that keep every handler's body focused on its one
business operation: loading the aggregate, and enforcing the cross-context
preconditions the *application* owns (ownership and organizer authorization). The
business invariants themselves stay in the domain; these helpers only decide the
application-level questions the domain cannot see (who is acting, does the
referenced thing exist).
"""

from __future__ import annotations

from datetime import datetime

from apps.applications.application.exceptions import (
    ApplicationError,
    CompetitionClosedError,
    PermissionDeniedError,
    SubmissionNotFoundError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    CompetitionCatalog,
    OrganizationReadModel,
    SubmissionRepository,
)
from apps.applications.domain.entities import Submission
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    CompetitionId,
    NominationId,
    ReviewerId,
    SubmissionId,
    SubmissionStatus,
    UserId,
)

__all__ = [
    "ensure_nomination_reachable",
    "ensure_owner",
    "ensure_reviewer",
    "load_submission",
    "parse_reviewer_id",
    "parse_submission_id",
    "parse_user_id",
    "try_resubmit_after_correction_edit",
]


def parse_submission_id(raw: str) -> SubmissionId:
    """Parse a ``SubmissionId`` from the command, translating validation errors."""
    with translate_domain_errors():
        return SubmissionId.from_string(raw)


def parse_user_id(raw: str) -> UserId:
    """Parse a ``UserId`` from the command, translating validation errors."""
    with translate_domain_errors():
        return UserId.from_string(raw)


def parse_reviewer_id(raw: str) -> ReviewerId:
    """Parse a ``ReviewerId`` from the command, translating validation errors."""
    with translate_domain_errors():
        return ReviewerId.from_string(raw)


def load_submission(repository: SubmissionRepository, submission_id: SubmissionId) -> Submission:
    """Load the submission or raise :class:`SubmissionNotFoundError`."""
    submission = repository.get(submission_id)
    if submission is None:
        raise SubmissionNotFoundError("Выступление не найдено — возможно, оно было удалено.")
    return submission


def ensure_owner(submission: Submission, actor: UserId) -> None:
    """Assert ``actor`` owns ``submission`` (the applicant), else deny."""
    if submission.applicant_id != actor:
        raise PermissionDeniedError("Это выступление принадлежит другому заявителю.")


def ensure_nomination_reachable(
    *,
    catalog: CompetitionCatalog,
    competition_id: CompetitionId,
    nomination_id: NominationId | None = None,
    now: datetime,
    message: str = "Регистрация закрыта: редактирование заявки недоступно.",
) -> None:
    """Assert the applicant may still get in at ``now``, else refuse.

    Two doors lead into a nomination and this helper opens either: registration while
    it is on, and the waitlist once it is off. A nomination with neither is the only
    case left to refuse, and the message says "закрыто" because from the applicant's
    side that is what happened — which door they would have used is the platform's
    business, not theirs.

    Without a ``nomination_id`` the question is the festival-wide one every step
    before the genre is picked has to ask: is there anywhere to get in at all? A
    festival whose genres have all closed but one, which keeps a list, must still let
    an applicant start — otherwise the waitlist is unreachable by the very people it
    exists for.
    """
    if catalog.accepts_submissions(competition_id=competition_id, nomination_id=nomination_id, now=now):
        return
    if catalog.accepts_waitlist(competition_id=competition_id, nomination_id=nomination_id, now=now):
        return
    raise CompetitionClosedError(message)


def ensure_reviewer(organization: OrganizationReadModel, reviewer_id: ReviewerId) -> None:
    """Assert ``reviewer_id`` is authorized to act as an organizer, else deny."""
    if not organization.can_review_submissions(reviewer_id=reviewer_id):
        raise PermissionDeniedError("Нет прав на рассмотрение заявок.")


def try_resubmit_after_correction_edit(*, submission: Submission, catalog: CompetitionCatalog, now: datetime) -> list[DomainEvent]:
    """Auto-resubmit a corrected submission back to SUBMITTED when valid.

    Used after applicant edits while the submission is in REQUIRES_CORRECTION.
    If validation is still incomplete, keep the status unchanged and continue.
    """
    if submission.status is not SubmissionStatus.REQUIRES_CORRECTION:
        return []
    performance = submission.performance
    if performance is None:
        return []
    policy = catalog.participation_policy(
        competition_id=submission.competition_id,
        nomination_id=performance.nomination_id,
        discipline_id=performance.discipline_id,
        age_category_id=performance.age_category_id,
        participant_group_id=performance.participant_group_id,
        participation_format_id=performance.participation_format_id,
    )
    if policy is None:
        return []
    try:
        with translate_domain_errors():
            return submission.submit(policy=policy, now=now)
    except ApplicationError:
        return []
