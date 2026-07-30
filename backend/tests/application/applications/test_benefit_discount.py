"""Discounts do not stack: a claimed benefit forfeits the multi-performance one.

An applicant who attaches a benefit certificate settles the reduction with the
organizer directly, so the order is priced at the plain list price - the
additional-performance discount is not applied on top of it.

These drive :func:`refresh_submission_refs` over the two aggregates directly,
which is where the order's cached prices are recomputed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.applications.application.orders._support import ref_from_submission, refresh_submission_refs
from apps.applications.domain.entities import Application, Submission
from apps.applications.domain.value_objects import (
    ApplicationId,
    AttachmentId,
    AttachmentType,
    CompetitionId,
    FileReference,
    Money,
    PriceSnapshot,
    SubmissionId,
    UserId,
)

from .fakes import FakeSubmissionRepository, uuid7_str

NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
LIST_PRICE = Money.of("300.00")
DISCOUNT_PERCENT = 50


def _priced_submission(*, competition_id: CompetitionId, applicant_id: UserId) -> Submission:
    submission, _ = Submission.draft(
        submission_id=SubmissionId.generate(),
        competition_id=competition_id,
        applicant_id=applicant_id,
        now=NOW,
    )
    submission.set_price_snapshot(price_snapshot=PriceSnapshot(price=LIST_PRICE, calculated_at=NOW), now=NOW)
    return submission


def _order_of_two() -> tuple[Application, FakeSubmissionRepository, Submission]:
    """A DRAFT order with two priced submissions attached, and its first submission."""
    competition_id = CompetitionId.from_string(uuid7_str())
    applicant_id = UserId.from_string(uuid7_str())
    application, _ = Application.create(
        application_id=ApplicationId.generate(),
        competition_id=competition_id,
        applicant_id=applicant_id,
        now=NOW,
    )
    submissions = FakeSubmissionRepository()
    first: Submission | None = None
    for _ in range(2):
        submission = _priced_submission(competition_id=competition_id, applicant_id=applicant_id)
        submissions.save(submission)
        application.attach_submission(ref=ref_from_submission(submission), now=NOW)
        first = first or submission
    assert first is not None
    return application, submissions, first


def _attach(submission: Submission, attachment_type: AttachmentType, filename: str) -> None:
    submission.add_attachment(
        attachment_id=AttachmentId.from_uuid(SubmissionId.generate().value),
        attachment_type=attachment_type,
        file=FileReference(filename),
        now=NOW,
    )


def _amounts(application: Application, submissions: FakeSubmissionRepository) -> list[str]:
    refresh_submission_refs(application, submissions, now=NOW, additional_performance_discount_percent=DISCOUNT_PERCENT)
    return [str(ref.price.amount) if ref.price is not None else "" for ref in application.submission_refs]


class TestBenefitSuppressesTheAdditionalPerformanceDiscount:
    def test_second_performance_is_discounted_without_a_benefit(self) -> None:
        application, submissions, _ = _order_of_two()
        assert _amounts(application, submissions) == ["300.00", "150.00"]

    def test_a_benefit_certificate_restores_the_list_price(self) -> None:
        application, submissions, first = _order_of_two()
        _attach(first, AttachmentType.BENEFIT, "uploads/benefit.pdf")
        submissions.save(first)
        assert _amounts(application, submissions) == ["300.00", "300.00"]

    def test_a_required_document_is_not_a_benefit_claim(self) -> None:
        # A competition may demand paperwork of everyone; that must not read as a
        # claim for a reduced fee, or the discount would vanish for the whole field.
        application, submissions, first = _order_of_two()
        _attach(first, AttachmentType.DOCUMENT, "uploads/birth-certificate.pdf")
        submissions.save(first)
        assert _amounts(application, submissions) == ["300.00", "150.00"]
