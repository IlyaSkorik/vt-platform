"""Query handlers (read use cases) for the Application (order) aggregate.

Side-effect-free reads returning view DTOs. Visibility is owner-scoped: only the
applicant who owns an order may read it (and only their own orders are listed).
"""

from __future__ import annotations

from datetime import datetime

from apps.applications.application.dto.orders import ApplicationSummaryView, ApplicationView
from apps.applications.application.dto.queries import (
    GetApplicationQuery,
    ListApplicationsQuery,
    ListDraftApplicationsQuery,
)
from apps.applications.application.exceptions import CompetitionCombinationNotFoundError, SubmissionInvariantViolationError
from apps.applications.application.interfaces import (
    ApplicationRepository,
    Clock,
    CompetitionCatalog,
    SubmissionRepository,
)
from apps.applications.domain.entities import Submission
from apps.applications.domain.value_objects import (
    ApplicationStatus,
    SubmissionStatus,
)

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

    While the order is still editable (DRAFT or SUBMITTED) its cached submission snapshots (status, price,
    display) can lag behind the live submissions the applicant is still editing in
    the wizard - a performance may have been priced after it was attached. To keep
    the previewed total honest, the refs are refreshed in memory before the view is
    built. This is a read-time projection: the aggregate is never saved, so no version
    is bumped and concurrent edits cannot conflict.
    """

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        clock: Clock,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock

    def handle(self, query: GetApplicationQuery) -> ApplicationView:
        application = load_application(self._applications, parse_application_id(query.application_id))
        ensure_owner(application, parse_user_id(query.requested_by))
        now = self._clock.utcnow()
        if application.status is ApplicationStatus.SUBMITTED:
            for ref in application.submission_refs:
                submission = self._submissions.get(ref.submission_id)
                if submission is None or submission.status is not SubmissionStatus.DRAFT:
                    continue
                self._try_submit_submission(submission, now=now)
        if application.status in {ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED}:
            refresh_submission_refs(
                application,
                self._submissions,
                now=now,
                additional_performance_discount_percent=self._catalog.additional_performance_discount_percent(
                    competition_id=application.competition_id
                ),
            )
        return ApplicationView.from_application(application)

    def _try_submit_submission(self, submission: Submission, *, now: datetime) -> None:
        performance = submission.performance
        if performance is None:
            return
        policy = self._catalog.participation_policy(
            competition_id=submission.competition_id,
            nomination_id=performance.nomination_id,
            discipline_id=performance.discipline_id,
            age_category_id=performance.age_category_id,
            participant_group_id=performance.participant_group_id,
            participation_format_id=performance.participation_format_id,
        )
        if policy is None:
            raise CompetitionCombinationNotFoundError("Такое сочетание жанра, номинации, возраста и формы участия фестиваль не принимает.")
        try:
            submission.submit(policy=policy, now=now)
        except SubmissionInvariantViolationError:
            return
        self._submissions.save(submission)


class ListApplicationsHandler:
    """Read use case: list the current applicant's applications (newest first)."""

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        clock: Clock,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock

    def handle(self, query: ListApplicationsQuery) -> tuple[ApplicationSummaryView, ...]:
        applicant_id = parse_user_id(query.applicant_id)
        now = self._clock.utcnow()
        apps = list(self._applications.list_by_applicant(applicant_id))
        for app in apps:
            if app.status is ApplicationStatus.SUBMITTED:
                for ref in app.submission_refs:
                    submission = self._submissions.get(ref.submission_id)
                    if submission is None or submission.status is not SubmissionStatus.DRAFT:
                        continue
                    self._try_submit_submission(submission, now=now)
            if app.status in {ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED}:
                refresh_submission_refs(
                    app,
                    self._submissions,
                    now=now,
                    additional_performance_discount_percent=self._catalog.additional_performance_discount_percent(competition_id=app.competition_id),
                )
        return tuple(ApplicationSummaryView.from_application(app) for app in apps)

    def _try_submit_submission(self, submission: Submission, *, now: datetime) -> None:
        performance = submission.performance
        if performance is None:
            return
        policy = self._catalog.participation_policy(
            competition_id=submission.competition_id,
            nomination_id=performance.nomination_id,
            discipline_id=performance.discipline_id,
            age_category_id=performance.age_category_id,
            participant_group_id=performance.participant_group_id,
            participation_format_id=performance.participation_format_id,
        )
        if policy is None:
            raise CompetitionCombinationNotFoundError("Такое сочетание жанра, номинации, возраста и формы участия фестиваль не принимает.")
        try:
            submission.submit(policy=policy, now=now)
        except SubmissionInvariantViolationError:
            return
        self._submissions.save(submission)


class ListDraftApplicationsHandler:
    """Read use case: list the current applicant's DRAFT applications."""

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        clock: Clock,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock

    def handle(self, query: ListDraftApplicationsQuery) -> tuple[ApplicationSummaryView, ...]:
        applicant_id = parse_user_id(query.applicant_id)
        now = self._clock.utcnow()
        apps = [app for app in self._applications.list_by_applicant(applicant_id) if app.status is ApplicationStatus.DRAFT]
        for app in apps:
            refresh_submission_refs(
                app,
                self._submissions,
                now=now,
                additional_performance_discount_percent=self._catalog.additional_performance_discount_percent(competition_id=app.competition_id),
            )
        return tuple(ApplicationSummaryView.from_application(app) for app in apps)
