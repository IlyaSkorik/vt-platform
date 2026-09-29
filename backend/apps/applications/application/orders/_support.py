"""Shared orchestration helpers for the Application (order) use cases.

Thin, framework-free helpers that keep each handler focused on its one operation:
parsing ids, loading the order, enforcing ownership, and the pull-based projection
that refreshes a submission reference's cached snapshot from the live Submission
aggregate (this context publishes no events yet, so the snapshot is refreshed on
demand rather than by an event subscriber).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from apps.applications.application.commands._support import try_resubmit_after_correction_edit
from apps.applications.application.exceptions import (
    ApplicationNotFoundError,
    PermissionDeniedError,
    translate_application_domain_errors,
    translate_domain_errors,
)
from apps.applications.application.interfaces import ApplicationRepository, CompetitionCatalog, SubmissionRepository
from apps.applications.domain.entities import Application, Submission
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    ApplicationId,
    AttachmentType,
    Money,
    PriceSnapshot,
    SubmissionRef,
    UserId,
)

__all__ = [
    "ensure_owner",
    "load_application",
    "parse_application_id",
    "parse_user_id",
    "ref_from_submission",
    "refresh_submission_refs",
    "resubmit_returned_submissions",
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
        raise ApplicationNotFoundError("Заявка не найдена — возможно, она была удалена.")
    return application


def ensure_owner(application: Application, actor: UserId) -> None:
    """Assert ``actor`` owns ``application`` (the applicant), else deny."""
    if application.applicant_id != actor:
        raise PermissionDeniedError("Эта заявка принадлежит другому заявителю.")


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


def _apply_additional_performance_discount(
    refs: list[SubmissionRef],
    *,
    discount_percent: int,
) -> list[SubmissionRef]:
    if discount_percent <= 0:
        return refs
    factor = Decimal("1") - (Decimal(discount_percent) / Decimal("100"))
    if factor < Decimal("0"):
        factor = Decimal("0")
    discounted: list[SubmissionRef] = []
    for index, ref in enumerate(refs):
        if index == 0 or ref.price is None:
            discounted.append(ref)
            continue
        new_amount = (ref.price.amount * factor).quantize(Decimal("0.01"))
        discounted.append(
            SubmissionRef(
                submission_id=ref.submission_id,
                performance_title=ref.performance_title,
                participant_display_name=ref.participant_display_name,
                nomination=ref.nomination,
                discipline=ref.discipline,
                status=ref.status,
                price=PriceSnapshot(
                    price=Money.of(new_amount, ref.price.currency),
                    calculated_at=ref.price.calculated_at,
                ),
            )
        )
    return discounted


def _claims_a_benefit(order_submissions: list[Submission]) -> bool:
    """Whether the order carries a benefit certificate on any of its submissions."""
    return any(attachment.type is AttachmentType.BENEFIT for submission in order_submissions for attachment in submission.attachments)


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


def resubmit_returned_submissions(
    application: Application,
    submissions: SubmissionRepository,
    catalog: CompetitionCatalog,
    *,
    now: datetime,
) -> list[DomainEvent]:
    """Put every returned entry of this order back in the queue, and say which moved.

    The order-level counterpart of the auto-resubmit an applicant's *content* edit
    already performs. It exists because an order can be returned for something that
    does not live on any submission — a receipt for the wrong festival, the wrong
    amount, someone else's transfer — and fixing that left the entries sitting in
    ``REQUIRES_CORRECTION`` with nobody able to move them: the applicant has no
    "submit again" of their own (placing an order only submits its drafts), and the
    organizer is offered no action in that status. The order stayed on the correction
    queue for good.

    An entry that cannot pass its own submission invariants stays where it is, exactly
    as it does after a content edit: coming back into the queue means "this is ready to
    be looked at again", and the domain is the one that decides whether it is.

    Saving is the caller's business — it owns the order's own write and must not end up
    doing two.
    """
    events: list[DomainEvent] = []
    for ref in application.submission_refs:
        submission = submissions.get(ref.submission_id)
        if submission is None:
            continue
        submission_events = try_resubmit_after_correction_edit(submission=submission, catalog=catalog, now=now)
        if not submission_events:
            continue
        submissions.save(submission)
        events += submission_events
    return events


def refresh_submission_refs(
    application: Application,
    submissions: SubmissionRepository,
    *,
    now: datetime,
    additional_performance_discount_percent: int = 0,
) -> None:
    """Refresh every attached submission's cached snapshot from its live aggregate.

    A pull-based projection: for each reference, the current Submission is loaded and
    its snapshot re-cached on the order (status/price/display), so a derived decision
    such as payment-readiness reads current data. A reference whose submission can no
    longer be loaded is left as-is.

    Discounts do not stack. An order that claims a benefit (a certificate attached
    to any of its submissions) is priced at the plain list price: the reduction the
    certificate earns is settled with the organizer, and the additional-performance
    discount is not applied on top of it.
    """
    refreshed_refs: list[SubmissionRef] = []
    loaded: list[Submission] = []
    for ref in application.submission_refs:
        submission = submissions.get(ref.submission_id)
        if submission is None:
            continue
        loaded.append(submission)
        refreshed_refs.append(ref_from_submission(submission))
    discount_percent = 0 if _claims_a_benefit(loaded) else additional_performance_discount_percent
    for ref in _apply_additional_performance_discount(
        refreshed_refs,
        discount_percent=discount_percent,
    ):
        with translate_application_domain_errors():
            application.refresh_submission_ref(ref=ref, now=now)
