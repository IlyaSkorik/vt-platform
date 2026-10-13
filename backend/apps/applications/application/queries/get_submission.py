"""Read use cases: fetch one submission in full, or its review history."""

from __future__ import annotations

from apps.applications.application.commands._support import (
    load_submission,
    parse_reviewer_id,
    parse_submission_id,
    parse_user_id,
    submission_editable_now,
)
from apps.applications.application.dto import SubmissionHistoryDto, SubmissionView
from apps.applications.application.dto.queries import (
    GetSubmissionHistoryQuery,
    GetSubmissionQuery,
)
from apps.applications.application.exceptions import PermissionDeniedError
from apps.applications.application.interfaces import (
    Clock,
    CompetitionCatalog,
    OrganizationReadModel,
    SubmissionRepository,
)
from apps.applications.domain.entities import Submission

__all__ = ["GetSubmissionHandler", "GetSubmissionHistoryHandler"]


def _ensure_can_view(submission: Submission, requested_by: str, organization: OrganizationReadModel) -> None:
    """Allow the owning applicant or any authorized organizer to view; else deny."""
    if submission.applicant_id == parse_user_id(requested_by):
        return
    if organization.can_review_submissions(reviewer_id=parse_reviewer_id(requested_by)):
        return
    raise PermissionDeniedError("Это выступление принадлежит другому заявителю.")


class GetSubmissionHandler:
    """Use case: fetch a submission in full (owner or an authorized organizer)."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
        catalog: CompetitionCatalog,
        clock: Clock,
    ) -> None:
        self._submissions = submissions
        self._organization = organization
        self._catalog = catalog
        self._clock = clock

    def handle(self, query: GetSubmissionQuery) -> SubmissionView:
        submission = load_submission(self._submissions, parse_submission_id(query.submission_id))
        _ensure_can_view(submission, query.requested_by, self._organization)
        # Whether the applicant may still change it travels with the entry: the card
        # that renders this view is the card with the editing controls on it, and it
        # must not offer what the endpoints behind those controls would refuse.
        return SubmissionView.from_submission(
            submission,
            editable=submission_editable_now(catalog=self._catalog, submission=submission, now=self._clock.utcnow()),
        )


class GetSubmissionHistoryHandler:
    """Use case: fetch a submission's review history (owner or an authorized organizer)."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
    ) -> None:
        self._submissions = submissions
        self._organization = organization

    def handle(self, query: GetSubmissionHistoryQuery) -> SubmissionHistoryDto:
        submission = load_submission(self._submissions, parse_submission_id(query.submission_id))
        _ensure_can_view(submission, query.requested_by, self._organization)
        return SubmissionHistoryDto.from_submission(submission)
