"""Read use cases: list the applicant's own submissions, or a competition's."""

from __future__ import annotations

from apps.applications.application.commands._support import (
    ensure_reviewer,
    parse_reviewer_id,
    parse_user_id,
)
from apps.applications.application.dto import SubmissionSummaryView
from apps.applications.application.dto.queries import (
    ListCompetitionSubmissionsQuery,
    ListMySubmissionsQuery,
)
from apps.applications.application.exceptions import translate_domain_errors
from apps.applications.application.interfaces import (
    OrganizationReadModel,
    SubmissionRepository,
)
from apps.applications.domain.value_objects import CompetitionId

__all__ = ["ListCompetitionSubmissionsHandler", "ListMySubmissionsHandler"]


class ListMySubmissionsHandler:
    """Use case: list the submissions owned by the current applicant."""

    def __init__(self, *, submissions: SubmissionRepository) -> None:
        self._submissions = submissions

    def handle(self, query: ListMySubmissionsQuery) -> tuple[SubmissionSummaryView, ...]:
        applicant_id = parse_user_id(query.applicant_id)
        submissions = self._submissions.list_by_applicant(applicant_id)
        return tuple(SubmissionSummaryView.from_submission(s) for s in submissions)


class ListCompetitionSubmissionsHandler:
    """Use case: list all submissions for a competition (authorized organizer only)."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
    ) -> None:
        self._submissions = submissions
        self._organization = organization

    def handle(self, query: ListCompetitionSubmissionsQuery) -> tuple[SubmissionSummaryView, ...]:
        ensure_reviewer(self._organization, parse_reviewer_id(query.requested_by))
        with translate_domain_errors():
            competition_id = CompetitionId.from_string(query.competition_id)
        submissions = self._submissions.list_by_competition(competition_id)
        return tuple(SubmissionSummaryView.from_submission(s) for s in submissions)
