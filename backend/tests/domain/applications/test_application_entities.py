"""Unit tests for the Application (order) aggregate root."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from apps.applications.domain.entities import Application
from apps.applications.domain.events import (
    AdditionalServiceRemoved,
    AdditionalServiceSelected,
    ApplicationAwaitingPayment,
    ApplicationCancelled,
    ApplicationCompleted,
    ApplicationCreated,
    ApplicationPaid,
    ApplicationSubmitted,
    EducationalOrganizationSelected,
    PaymentReceiptRemoved,
    PaymentReceiptUploaded,
    SubmissionAttachedToApplication,
    SubmissionDetachedFromApplication,
)
from apps.applications.domain.exceptions import (
    ApplicationNotEditableError,
    DirectApplicationConstructionError,
    DuplicateServiceLineError,
    DuplicateSubmissionRefError,
    IllegalApplicationStatusTransitionError,
    MissingRequiredConsentError,
    NoSubmissionsError,
    NotAllSubmissionsApprovedError,
    PaymentReceiptNotAllowedError,
    PaymentReceiptNotFoundError,
    ServiceLineNotFoundError,
    SubmissionRefNotFoundError,
    TooManyPaymentReceiptsError,
)
from apps.applications.domain.value_objects import (
    ApplicationId,
    ApplicationStatus,
    CompetitionId,
    Consent,
    EducationalOrganizationId,
    FileReference,
    Money,
    OrganizationName,
    PaymentReceiptId,
    PriceSnapshot,
    ServiceId,
    ServiceLine,
    SubmissionId,
    SubmissionRef,
    SubmissionStatus,
    UserId,
)

NOW = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)


def _competition_id() -> CompetitionId:
    return CompetitionId.from_uuid(ApplicationId.generate().value)


def _user_id() -> UserId:
    return UserId.from_uuid(ApplicationId.generate().value)


def _new_application() -> Application:
    application, _ = Application.create(
        application_id=ApplicationId.generate(),
        competition_id=_competition_id(),
        applicant_id=_user_id(),
        now=NOW,
    )
    return application


def _ref(*, status: SubmissionStatus, amount: str | None = "300.00", submission_id: SubmissionId | None = None) -> SubmissionRef:
    price = PriceSnapshot(price=Money.of(amount), calculated_at=NOW) if amount is not None else None
    return SubmissionRef(
        submission_id=submission_id or SubmissionId.generate(),
        performance_title="Swan Lake",
        participant_display_name="Ivanova Anna",
        nomination="Choreography",
        discipline="Ballet",
        status=status,
        price=price,
    )


def _service(amount: str = "25.00", quantity: int = 1) -> ServiceLine:
    return ServiceLine(service_id=ServiceId.from_uuid(ApplicationId.generate().value), name="T-shirt", unit_price=Money.of(amount), quantity=quantity)


class TestCreation:
    def test_create_starts_draft_with_zero_total_and_history(self) -> None:
        application, events = Application.create(
            application_id=ApplicationId.generate(),
            competition_id=_competition_id(),
            applicant_id=_user_id(),
            now=NOW,
        )
        assert application.status is ApplicationStatus.DRAFT
        assert application.is_draft()
        assert application.submission_count == 0
        assert application.total_price is not None
        assert application.total_price.amount == Money.of("0.00").amount
        assert [type(e) for e in events] == [ApplicationCreated]
        assert len(application.status_history) == 1
        assert application.status_history[0].from_status is None
        assert application.status_history[0].to_status is ApplicationStatus.DRAFT
        assert application.version == 1

    def test_direct_construction_is_refused(self) -> None:
        with pytest.raises(DirectApplicationConstructionError):
            Application(
                _token=object(),
                _id=ApplicationId.generate(),
                _competition_id=_competition_id(),
                _applicant_id=_user_id(),
                _status=ApplicationStatus.DRAFT,
                _created_at=NOW,
                _updated_at=NOW,
            )


class TestComposition:
    def test_select_educational_organization(self) -> None:
        application = _new_application()
        org_id = EducationalOrganizationId.from_uuid(ApplicationId.generate().value)
        events = application.select_educational_organization(
            educational_organization_id=org_id,
            organization_name=OrganizationName("Music School"),
            now=NOW,
        )
        assert application.educational_organization_id == org_id
        assert application.organization_name == OrganizationName("Music School")
        assert [type(e) for e in events] == [EducationalOrganizationSelected]

    def test_attach_submission_adds_ref_and_recomputes_total(self) -> None:
        application = _new_application()
        events = application.attach_submission(ref=_ref(status=SubmissionStatus.DRAFT, amount="300.00"), now=NOW)
        assert application.submission_count == 1
        assert application.total_price is not None
        assert application.total_price.submissions_total == Money.of("300.00")
        assert [type(e) for e in events] == [SubmissionAttachedToApplication]

    def test_attach_duplicate_submission_is_rejected(self) -> None:
        application = _new_application()
        ref = _ref(status=SubmissionStatus.DRAFT)
        application.attach_submission(ref=ref, now=NOW)
        with pytest.raises(DuplicateSubmissionRefError):
            application.attach_submission(ref=ref, now=NOW)

    def test_detach_submission_removes_ref(self) -> None:
        application = _new_application()
        ref = _ref(status=SubmissionStatus.DRAFT)
        application.attach_submission(ref=ref, now=NOW)
        events = application.detach_submission(submission_id=ref.submission_id, now=NOW)
        assert application.submission_count == 0
        assert [type(e) for e in events] == [SubmissionDetachedFromApplication]

    def test_detach_unknown_submission_is_rejected(self) -> None:
        application = _new_application()
        with pytest.raises(SubmissionRefNotFoundError):
            application.detach_submission(submission_id=SubmissionId.generate(), now=NOW)

    def test_total_is_sum_of_submissions_and_services(self) -> None:
        application = _new_application()
        application.attach_submission(ref=_ref(status=SubmissionStatus.DRAFT, amount="300.00"), now=NOW)
        application.attach_submission(ref=_ref(status=SubmissionStatus.DRAFT, amount="150.00"), now=NOW)
        application.add_service(service_line=_service(amount="25.00", quantity=2), now=NOW)
        total = application.total_price
        assert total is not None
        assert total.submissions_total == Money.of("450.00")
        assert total.services_total == Money.of("50.00")
        assert total.total == Money.of("500.00")

    def test_add_duplicate_service_is_rejected(self) -> None:
        application = _new_application()
        service = _service()
        application.add_service(service_line=service, now=NOW)
        with pytest.raises(DuplicateServiceLineError):
            application.add_service(service_line=service, now=NOW)

    def test_remove_service(self) -> None:
        application = _new_application()
        service = _service()
        add_events = application.add_service(service_line=service, now=NOW)
        assert [type(e) for e in add_events] == [AdditionalServiceSelected]
        events = application.remove_service(service_id=service.service_id, now=NOW)
        assert application.service_lines == ()
        assert [type(e) for e in events] == [AdditionalServiceRemoved]

    def test_remove_unknown_service_is_rejected(self) -> None:
        application = _new_application()
        with pytest.raises(ServiceLineNotFoundError):
            application.remove_service(service_id=ServiceId.from_uuid(ApplicationId.generate().value), now=NOW)

    def test_record_consents(self) -> None:
        application = _new_application()
        application.record_consents(consents=[Consent(code="personal_data", version="v1", accepted_at=NOW)], now=NOW)
        assert len(application.consents) == 1


class TestSubmit:
    def test_submit_requires_at_least_one_submission(self) -> None:
        application = _new_application()
        with pytest.raises(NoSubmissionsError):
            application.submit(now=NOW)

    def test_submit_enforces_required_consents(self) -> None:
        application = _new_application()
        application.attach_submission(ref=_ref(status=SubmissionStatus.DRAFT), now=NOW)
        with pytest.raises(MissingRequiredConsentError):
            application.submit(required_consent_codes=frozenset({"personal_data"}), now=NOW)

    def test_submit_transitions_and_freezes_total(self) -> None:
        application = _new_application()
        application.attach_submission(ref=_ref(status=SubmissionStatus.SUBMITTED, amount="300.00"), now=NOW)
        application.record_consents(consents=[Consent(code="personal_data", version="v1", accepted_at=NOW)], now=NOW)
        events = application.submit(required_consent_codes=frozenset({"personal_data"}), now=NOW)
        assert application.status is ApplicationStatus.SUBMITTED
        assert [type(e) for e in events] == [ApplicationSubmitted]
        submitted = events[0]
        assert isinstance(submitted, ApplicationSubmitted)
        assert submitted.amount == "300.00"

    def test_composition_still_open_after_submit(self) -> None:
        """A submitted order still takes another entry — the applicant is not done
        until they pay, and adding a second act must not mean starting over."""
        application = _submitted_application(amount="300.00")
        application.attach_submission(ref=_ref(status=SubmissionStatus.SUBMITTED), now=NOW)
        assert application.submission_count == 2

    def test_composition_frozen_once_payment_is_awaited(self) -> None:
        """Requesting payment is what closes the order: the applicant has been quoted
        a figure, so the basket it was computed from can no longer change."""
        application = _awaiting_payment_application(amount="300.00")
        with pytest.raises(ApplicationNotEditableError):
            application.attach_submission(ref=_ref(status=SubmissionStatus.SUBMITTED), now=NOW)

    def test_total_is_immutable_once_payment_is_awaited(self) -> None:
        """Past the quote a refresh still updates the cached snapshot but must not
        move the total — otherwise a late organizer edit would change what is owed."""
        application = _awaiting_payment_application(amount="300.00")
        ref = application.submission_refs[0]
        frozen_total = application.total_price
        later = NOW + timedelta(days=1)
        application.refresh_submission_ref(ref=_ref(status=SubmissionStatus.APPROVED, amount="999.00", submission_id=ref.submission_id), now=later)
        assert application.total_price == frozen_total


class TestPaymentReadinessAndLifecycle:
    def test_request_payment_requires_all_submissions_approved(self) -> None:
        application = _new_application()
        ref = _ref(status=SubmissionStatus.SUBMITTED)
        application.attach_submission(ref=ref, now=NOW)
        application.submit(now=NOW)
        with pytest.raises(NotAllSubmissionsApprovedError):
            application.request_payment(now=NOW)

    def test_full_happy_path_to_completed(self) -> None:
        application = _new_application()
        ref = _ref(status=SubmissionStatus.SUBMITTED, amount="300.00")
        application.attach_submission(ref=ref, now=NOW)
        application.submit(now=NOW)
        application.refresh_submission_ref(ref=_ref(status=SubmissionStatus.APPROVED, amount="300.00", submission_id=ref.submission_id), now=NOW)
        # Each transition is asserted through its event (not a chained status read,
        # which mypy would narrow across the intervening mutations).
        assert [type(e) for e in application.request_payment(now=NOW)] == [ApplicationAwaitingPayment]
        assert [type(e) for e in application.mark_paid(now=NOW)] == [ApplicationPaid]
        assert application.paid_at == NOW
        assert [type(e) for e in application.complete(now=NOW)] == [ApplicationCompleted]
        assert application.status is ApplicationStatus.COMPLETED
        # DRAFT -> SUBMITTED -> WAITING_PAYMENT -> PAID -> COMPLETED (+ creation) = 5 entries.
        assert len(application.status_history) == 5

    def test_request_payment_from_draft_is_illegal_even_if_approved(self) -> None:
        application = _new_application()
        application.attach_submission(ref=_ref(status=SubmissionStatus.APPROVED), now=NOW)
        with pytest.raises(IllegalApplicationStatusTransitionError):
            application.request_payment(now=NOW)

    def test_cancel_from_draft(self) -> None:
        application = _new_application()
        events = application.cancel(now=NOW)
        assert application.status is ApplicationStatus.CANCELLED
        assert [type(e) for e in events] == [ApplicationCancelled]

    def test_cannot_cancel_once_paid(self) -> None:
        application = _new_application()
        ref = _ref(status=SubmissionStatus.APPROVED, amount="300.00")
        application.attach_submission(ref=ref, now=NOW)
        application.submit(now=NOW)
        application.request_payment(now=NOW)
        application.mark_paid(now=NOW)
        with pytest.raises(IllegalApplicationStatusTransitionError):
            application.cancel(now=NOW)


class TestPaymentReceipts:
    def test_each_upload_adds_a_receipt(self) -> None:
        # A fee settled by two transfers has two slips; the second must not erase
        # the first, or the order looks half-paid to whoever reconciles it.
        application = _new_application()
        application.upload_payment_receipt(file=FileReference("first.pdf"), now=NOW)
        events = application.upload_payment_receipt(file=FileReference("second.pdf"), now=NOW)

        assert [receipt.file.value for receipt in application.payment_receipts] == ["first.pdf", "second.pdf"]
        assert isinstance(events[0], PaymentReceiptUploaded)
        assert events[0].receipt_id == application.payment_receipts[1].id

    def test_receipts_carry_distinct_ids(self) -> None:
        application = _new_application()
        application.upload_payment_receipt(file=FileReference("first.pdf"), now=NOW)
        application.upload_payment_receipt(file=FileReference("second.pdf"), now=NOW)
        assert len({receipt.id for receipt in application.payment_receipts}) == 2

    def test_remove_detaches_only_the_receipt_named(self) -> None:
        application = _new_application()
        application.upload_payment_receipt(file=FileReference("keep.pdf"), now=NOW)
        application.upload_payment_receipt(file=FileReference("wrong.pdf"), now=NOW)
        wrong = application.payment_receipts[1]

        events = application.remove_payment_receipt(receipt_id=wrong.id, now=NOW)

        assert [receipt.file.value for receipt in application.payment_receipts] == ["keep.pdf"]
        assert isinstance(events[0], PaymentReceiptRemoved)

    def test_removing_a_receipt_that_is_not_there_is_refused(self) -> None:
        application = _new_application()
        application.upload_payment_receipt(file=FileReference("only.pdf"), now=NOW)
        with pytest.raises(PaymentReceiptNotFoundError):
            application.remove_payment_receipt(receipt_id=PaymentReceiptId.generate(), now=NOW)

    def test_has_payment_receipt_tracks_the_list(self) -> None:
        application = _new_application()
        assert application.has_payment_receipt is False
        application.upload_payment_receipt(file=FileReference("only.pdf"), now=NOW)
        assert application.has_payment_receipt is True
        application.remove_payment_receipt(receipt_id=application.payment_receipts[0].id, now=NOW)
        assert application.has_payment_receipt is False

    def test_the_pile_is_capped(self) -> None:
        application = _new_application()
        for index in range(20):
            application.upload_payment_receipt(file=FileReference(f"transfer-{index}.pdf"), now=NOW)
        with pytest.raises(TooManyPaymentReceiptsError):
            application.upload_payment_receipt(file=FileReference("one-too-many.pdf"), now=NOW)

    def test_a_settled_order_accepts_no_change_to_its_receipts(self) -> None:
        application = _new_application()
        application.upload_payment_receipt(file=FileReference("paid.pdf"), now=NOW)
        receipt_id = application.payment_receipts[0].id
        application.cancel(now=NOW)
        with pytest.raises(PaymentReceiptNotAllowedError):
            application.upload_payment_receipt(file=FileReference("late.pdf"), now=NOW)
        with pytest.raises(PaymentReceiptNotAllowedError):
            application.remove_payment_receipt(receipt_id=receipt_id, now=NOW)


class TestRehydrate:
    def test_rehydrate_roundtrip(self) -> None:
        original = _submitted_application(amount="300.00")
        restored = Application.rehydrate(
            application_id=original.id,
            competition_id=original.competition_id,
            applicant_id=original.applicant_id,
            status=original.status,
            created_at=original.created_at,
            updated_at=original.updated_at,
            submission_refs=original.submission_refs,
            service_lines=original.service_lines,
            consents=original.consents,
            total_price=original.total_price,
            status_history=original.status_history,
            version=original.version,
        )
        assert restored == original
        assert restored.status is ApplicationStatus.SUBMITTED
        assert restored.submission_count == 1
        assert restored.total_price == original.total_price


def _submitted_application(*, amount: str) -> Application:
    application = _new_application()
    application.attach_submission(ref=_ref(status=SubmissionStatus.SUBMITTED, amount=amount), now=NOW)
    application.submit(now=NOW)
    return application


def _awaiting_payment_application(*, amount: str) -> Application:
    """An order past the point of no return: quoted a total and waiting to be paid.

    This — not ``submit`` — is where the order's composition and total freeze, so it
    is the fixture the immutability tests need.
    """
    application = _new_application()
    ref = _ref(status=SubmissionStatus.SUBMITTED, amount=amount)
    application.attach_submission(ref=ref, now=NOW)
    application.submit(now=NOW)
    application.refresh_submission_ref(ref=_ref(status=SubmissionStatus.APPROVED, amount=amount, submission_id=ref.submission_id), now=NOW)
    application.request_payment(now=NOW)
    return application
