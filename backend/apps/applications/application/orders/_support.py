"""Shared orchestration helpers for the Application (order) use cases.

Thin, framework-free helpers that keep each handler focused on its one operation:
parsing ids, loading the order, enforcing ownership, and the pull-based projection
that refreshes a submission reference's cached snapshot from the live Submission
aggregate (this context publishes no events yet, so the snapshot is refreshed on
demand rather than by an event subscriber).
"""

from __future__ import annotations

from datetime import datetime

from apps.applications.application.exceptions import (
    ApplicationNotFoundError,
    PermissionDeniedError,
    translate_application_domain_errors,
    translate_domain_errors,
)
from apps.applications.application.interfaces import ApplicationRepository, SubmissionRepository
from apps.applications.domain.entities import Application, Submission
from apps.applications.domain.value_objects import ApplicationId, SubmissionRef, UserId

__all__ = [
    "ensure_owner",
    "load_application",
    "parse_application_id",
    "parse_user_id",
    "ref_from_submission",
    "refresh_submission_refs",
]


def parse_application_id(raw: str) -> ApplicationId:
    """Parse an ``ApplicationId`` from a command, translating validation errors."""
    with translate_application_domain_errors():
        return ApplicationId.from_string(raw)


def parse_user_id(raw: str) -> UserId:
    """Parse a ``UserId`` from a command, translating validation errors.

    ``UserId`` belongs to the shared value-object tree (its error is a
    ``ValueObjectValidationError``), so it is translated with
    :func:`translate_domain_errors`, not the order-specific translator.
    """
    with translate_domain_errors():
        return UserId.from_string(raw)


def load_application(applications: ApplicationRepository, application_id: ApplicationId) -> Application:
    """Load the application or raise :class:`ApplicationNotFoundError`."""
    application = applications.get(application_id)
    if application is None:
        raise ApplicationNotFoundError(f"No application {application_id.json()}.")
    return application


def ensure_owner(application: Application, actor: UserId) -> None:
    """Assert ``actor`` owns ``application`` (the applicant), else deny."""
    if application.applicant_id != actor:
        raise PermissionDeniedError("Only the applicant who owns this application may perform this action.")


def ref_from_submission(submission: Submission) -> SubmissionRef:
    """Build the order's cached snapshot of a submission from its current state.

    The nomination/discipline are carried as their configuration id references (the
    Submission holds ids, not labels); resolving them to human labels is a future
    enhancement once the Competition ACL exposes combination labels.
    """
    performance = submission.performance
    participants = submission.participants
    lead_name = participants[0].display_name if participants else ""
    return SubmissionRef(
        submission_id=submission.id,
        performance_title=performance.title.value if performance is not None else "",
        participant_display_name=lead_name,
        nomination=performance.nomination_id.json() if performance is not None else "",
        discipline=performance.discipline_id.json() if performance is not None else "",
        status=submission.status,
        price=submission.price_snapshot,
    )


def load_order_submissions(application: Application, submissions: SubmissionRepository) -> list[Submission]:
    """Load the live Submission aggregates the order references (skipping any gone)."""
    loaded: list[Submission] = []
    for ref in application.submission_refs:
        submission = submissions.get(ref.submission_id)
        if submission is not None:
            loaded.append(submission)
    return loaded


def order_participation_format_ids(order_submissions: list[Submission]) -> frozenset[str]:
    """The set of participation-format ids used across the order's performances."""
    return frozenset(submission.performance.participation_format_id.json() for submission in order_submissions if submission.performance is not None)


def refresh_submission_refs(application: Application, submissions: SubmissionRepository, *, now: datetime) -> None:
    """Refresh every attached submission's cached snapshot from its live aggregate.

    A pull-based projection: for each reference, the current Submission is loaded and
    its snapshot re-cached on the order (status/price/display), so a derived decision
    such as payment-readiness reads current data. A reference whose submission can no
    longer be loaded is left as-is.
    """
    for ref in application.submission_refs:
        submission = submissions.get(ref.submission_id)
        if submission is None:
            continue
        with translate_application_domain_errors():
            application.refresh_submission_ref(ref=ref_from_submission(submission), now=now)
