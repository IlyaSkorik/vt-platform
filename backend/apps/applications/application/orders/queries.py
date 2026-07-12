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
from apps.applications.application.interfaces import ApplicationRepository
from apps.applications.domain.value_objects import ApplicationStatus

from ._support import ensure_owner, load_application, parse_application_id, parse_user_id

__all__ = [
    "GetApplicationHandler",
    "ListApplicationsHandler",
    "ListDraftApplicationsHandler",
]


class GetApplicationHandler:
    """Read use case: retrieve one application in full (owner only)."""

    def __init__(self, *, applications: ApplicationRepository) -> None:
        self._applications = applications

    def handle(self, query: GetApplicationQuery) -> ApplicationView:
        application = load_application(self._applications, parse_application_id(query.application_id))
        ensure_owner(application, parse_user_id(query.requested_by))
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
