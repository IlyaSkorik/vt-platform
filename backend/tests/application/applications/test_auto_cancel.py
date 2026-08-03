"""Unit tests for the deferred unpaid-order auto-cancellation use case."""

from __future__ import annotations

from datetime import UTC, datetime

from apps.applications.application.orders import AutoCancelUnpaidApplicationHandler
from apps.applications.domain.entities import Application
from apps.applications.domain.value_objects import (
    ApplicationId,
    ApplicationStatus,
    CompetitionId,
    FileReference,
    PaymentReceipt,
    PaymentReceiptId,
    UserId,
)
from apps.applications.infrastructure.models.base import uuid7

from .fakes import (
    FakeApplicationRepository,
    FakeClock,
    FakeIdentityReadModel,
    FakeSubmissionRepository,
    RecordingEventPublisher,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


class RecordingNotifier:
    def __init__(self) -> None:
        self.submitted: list[str] = []
        self.awaiting: list[str] = []
        self.cancelled: list[str] = []

    def notify_application_submitted(self, *, email: str, applicant_name: str) -> None:
        self.submitted.append(email)

    def notify_application_awaiting_payment(self, *, email: str, applicant_name: str, deadline: datetime) -> None:
        self.awaiting.append(email)

    def notify_application_auto_cancelled(self, *, email: str, applicant_name: str) -> None:
        self.cancelled.append(email)


def _application(status: ApplicationStatus, *, with_receipt: bool) -> Application:
    receipts = [PaymentReceipt(id=PaymentReceiptId.generate(), file=FileReference("receipt.pdf"), uploaded_at=_NOW)] if with_receipt else []
    return Application.rehydrate(
        application_id=ApplicationId.generate(),
        competition_id=CompetitionId.from_uuid(uuid7()),
        applicant_id=UserId.from_uuid(uuid7()),
        status=status,
        created_at=_NOW,
        updated_at=_NOW,
        payment_receipts=receipts,
    )


def _handler(applications: FakeApplicationRepository) -> tuple[AutoCancelUnpaidApplicationHandler, RecordingNotifier]:
    notifier = RecordingNotifier()
    handler = AutoCancelUnpaidApplicationHandler(
        applications=applications,
        submissions=FakeSubmissionRepository(),
        clock=FakeClock(),
        events=RecordingEventPublisher(),
        identity=FakeIdentityReadModel(),
        notifier=notifier,
    )
    return handler, notifier


def test_cancels_submitted_order_without_receipt_and_notifies() -> None:
    applications = FakeApplicationRepository()
    application = _application(ApplicationStatus.SUBMITTED, with_receipt=False)
    applications.save(application)
    handler, notifier = _handler(applications)

    handler.handle(application.id.json())

    reloaded = applications.get(application.id)
    assert reloaded is not None
    assert reloaded.status is ApplicationStatus.CANCELLED
    assert notifier.cancelled == ["applicant@example.com"]


def test_keeps_order_when_receipt_attached() -> None:
    applications = FakeApplicationRepository()
    application = _application(ApplicationStatus.SUBMITTED, with_receipt=True)
    applications.save(application)
    handler, notifier = _handler(applications)

    handler.handle(application.id.json())

    reloaded = applications.get(application.id)
    assert reloaded is not None
    assert reloaded.status is ApplicationStatus.SUBMITTED
    assert notifier.cancelled == []


def test_noop_when_already_paid() -> None:
    applications = FakeApplicationRepository()
    application = _application(ApplicationStatus.PAID, with_receipt=False)
    applications.save(application)
    handler, notifier = _handler(applications)

    handler.handle(application.id.json())

    reloaded = applications.get(application.id)
    assert reloaded is not None
    assert reloaded.status is ApplicationStatus.PAID
    assert notifier.cancelled == []


def test_noop_when_application_missing() -> None:
    applications = FakeApplicationRepository()
    handler, notifier = _handler(applications)

    handler.handle(ApplicationId.generate().json())  # unknown id

    assert notifier.cancelled == []
