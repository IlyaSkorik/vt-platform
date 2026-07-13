"""Query handlers (read use cases) for the Application (order) aggregate.

Side-effect-free reads returning view DTOs. Visibility is owner-scoped: only the
applicant who owns an order may read it (and only their own orders are listed).
"""

from __future__ import annotations

from apps.applications.application.dto.orders import ApplicationSummaryView, ApplicationView
from apps.applications.application.dto.queries import (
    GetApplicationQuery,
    ListApplicationsQuery,
    ListDraftApplicationsQuery,
)
from apps.applications.application.interfaces import (
    ApplicationRepository,
    Clock,
    SubmissionRepository,
)
from apps.applications.domain.value_objects import ApplicationStatus

from ._support import (
    ensure_owner,
    load_application,
    parse_application_id,
    parse_user_id,
    refresh_submission_refs,
)

__all__ = [
    "GetApplicationHandler",
    "ListApplicationsHandler",
    "ListDraftApplicationsHandler",
]


class GetApplicationHandler:
    """Read use case: retrieve one application in full (owner only).

    While the order is still a DRAFT its cached submission snapshots (status, price,
    display) can lag behind the live submissions the applicant is still editing in
    the wizard - a performance may have been priced after it was attached. To keep
    the previewed total honest, the refs are refreshed in memory before the view is
    built. This is a read-time projection: the aggregate is never saved, so no version
    is bumped and concurrent edits cannot conflict. Once submitted the total is frozen
    and left untouched.
    """

    def __init__(self, *, applications: ApplicationRepository, submissions: SubmissionRepository, clock: Clock) -> None:
        self._applications = applications
        self._submissions = submissions
        self._clock = clock

    def handle(self, query: GetApplicationQuery) -> ApplicationView:
        application = load_application(self._applications, parse_application_id(query.application_id))
        ensure_owner(application, parse_user_id(query.requested_by))
        if application.status is ApplicationStatus.DRAFT:
            refresh_submission_refs(application, self._submissions, now=self._clock.utcnow())
        return ApplicationView.from_application(application)


class ListApplicationsHandler:
    """Read use case: list the current applicant's applications (newest first)."""

    def __init__(self, *, applications: ApplicationRepository) -> None:
        self._applications = applications

    def handle(self, query: ListApplicationsQuery) -> tuple[ApplicationSummaryView, ...]:
        applicant_id = parse_user_id(query.applicant_id)
        return tuple(ApplicationSummaryView.from_application(app) for app in self._applications.list_by_applicant(applicant_id))


class ListDraftApplicationsHandler:
    """Read use case: list the current applicant's DRAFT applications."""

    def __init__(self, *, applications: ApplicationRepository) -> None:
        self._applications = applications

    def handle(self, query: ListDraftApplicationsQuery) -> tuple[ApplicationSummaryView, ...]:
        applicant_id = parse_user_id(query.applicant_id)
        return tuple(
            ApplicationSummaryView.from_application(app)
            for app in self._applications.list_by_applicant(applicant_id)
            if app.status is ApplicationStatus.DRAFT
        )
