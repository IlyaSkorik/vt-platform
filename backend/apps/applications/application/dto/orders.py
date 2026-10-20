"""Result & view DTOs for the Application (order) use cases.

Immutable, primitive-only output shapes projecting the :class:`Application`
aggregate (its submission references, service lines, consents, total price and
status history) into flat, serialization-agnostic views. Ids/enums render as
strings, money as a decimal string, temporal values as ``datetime``. Command
handlers return an :class:`ApplicationOperationResultDto`; query handlers return
the views directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.applications.domain.entities import Application
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    ApplicationStatusChange,
    Consent,
    ServiceLine,
    SubmissionRef,
    TotalPriceSnapshot,
)

__all__ = [
    "ApplicationOperationResultDto",
    "ApplicationStatusChangeView",
    "ApplicationSummaryView",
    "ApplicationView",
    "ConsentView",
    "PayerView",
    "PaymentReceiptView",
    "ServiceLineView",
    "SubmissionRefView",
    "TotalPriceView",
]


@dataclass(frozen=True, slots=True)
class SubmissionRefView:
    """A flat read view of a cached submission reference on the order."""

    submission_id: str
    performance_title: str
    participant_display_name: str
    nomination: str
    #: The genre's id, which is what the cabinet needs rather than its label: the
    #: organizer's editing freeze is per genre, and the card has to know which one
    #: this entry is in to say whether its files may still be touched. ``None`` for
    #: an entry with no performance yet.
    nomination_id: str | None
    discipline: str
    status: str
    price_amount: str | None
    currency: str | None

    @classmethod
    def from_ref(cls, ref: SubmissionRef) -> SubmissionRefView:
        return cls(
            submission_id=ref.submission_id.json(),
            performance_title=ref.performance_title,
            participant_display_name=ref.participant_display_name,
            nomination=ref.nomination,
            nomination_id=ref.nomination_id.json() if ref.nomination_id is not None else None,
            discipline=ref.discipline,
            status=ref.status.value,
            price_amount=str(ref.price.amount) if ref.price is not None else None,
            currency=ref.price.currency.value if ref.price is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ServiceLineView:
    """A flat read view of a selected additional service on the order."""

    service_id: str
    name: str
    unit_amount: str
    quantity: int
    line_amount: str
    currency: str

    @classmethod
    def from_line(cls, line: ServiceLine) -> ServiceLineView:
        return cls(
            service_id=line.service_id.json(),
            name=line.name,
            unit_amount=str(line.unit_price.amount),
            quantity=line.quantity,
            line_amount=str(line.line_total.amount),
            currency=line.unit_price.currency.value,
        )


@dataclass(frozen=True, slots=True)
class ConsentView:
    """A flat read view of an accepted consent on the order."""

    code: str
    version: str
    accepted_at: datetime

    @classmethod
    def from_consent(cls, consent: Consent) -> ConsentView:
        return cls(code=consent.code, version=consent.version, accepted_at=consent.accepted_at)


@dataclass(frozen=True, slots=True)
class TotalPriceView:
    """A flat read view of the order's frozen total price snapshot."""

    total_amount: str
    submissions_amount: str
    services_amount: str
    currency: str
    calculated_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: TotalPriceSnapshot) -> TotalPriceView:
        return cls(
            total_amount=str(snapshot.total.amount),
            submissions_amount=str(snapshot.submissions_total.amount),
            services_amount=str(snapshot.services_total.amount),
            currency=snapshot.total.currency.value,
            calculated_at=snapshot.calculated_at,
        )


@dataclass(frozen=True, slots=True)
class ApplicationStatusChangeView:
    """A flat read view of one order status-history entry."""

    from_status: str | None
    to_status: str
    occurred_at: datetime

    @classmethod
    def from_change(cls, change: ApplicationStatusChange) -> ApplicationStatusChangeView:
        return cls(
            from_status=change.from_status.value if change.from_status is not None else None,
            to_status=change.to_status.value,
            occurred_at=change.occurred_at,
        )


@dataclass(frozen=True, slots=True)
class PaymentReceiptView:
    """A flat read view of one of the order's payment receipts."""

    id: str
    file_reference: str
    uploaded_at: datetime


@dataclass(frozen=True, slots=True)
class PayerView:
    """The person the festival's contract for the order is signed with."""

    last_name: str
    first_name: str
    middle_name: str | None
    full_name: str


@dataclass(frozen=True, slots=True)
class ApplicationView:
    """A flat, immutable read view of the whole :class:`Application` aggregate."""

    id: str
    competition_id: str
    applicant_id: str
    status: str
    educational_organization_id: str | None
    organization_name: str | None
    payer: PayerView | None
    submissions: tuple[SubmissionRefView, ...]
    services: tuple[ServiceLineView, ...]
    consents: tuple[ConsentView, ...]
    total_price: TotalPriceView | None
    status_history: tuple[ApplicationStatusChangeView, ...]
    payment_receipts: tuple[PaymentReceiptView, ...]
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int
    #: Whether the applicant may still change anything in this order: any of its
    #: numbers still editable, or — while it is a draft — any door into the festival
    #: still open. The same rule the command use cases enforce, answered once so the
    #: «Редактировать» button is absent rather than present and refused.
    #:
    #: Computed on the detail read and nowhere else. Command results leave it at
    #: ``True`` and mean nothing by it: a command that was just accepted was allowed,
    #: and the clients refetch the order after every change rather than believing the
    #: echo.
    editable: bool = True

    @classmethod
    def from_application(cls, application: Application, *, editable: bool = True) -> ApplicationView:
        org = application.organization_name
        payer = application.payer_name
        total = application.total_price
        return cls(
            id=application.id.json(),
            competition_id=application.competition_id.json(),
            applicant_id=application.applicant_id.json(),
            status=application.status.value,
            educational_organization_id=(
                application.educational_organization_id.json() if application.educational_organization_id is not None else None
            ),
            organization_name=org.value if org is not None else None,
            payer=(
                PayerView(
                    last_name=payer.last_name,
                    first_name=payer.first_name,
                    middle_name=payer.middle_name,
                    full_name=payer.full_name,
                )
                if payer is not None
                else None
            ),
            submissions=tuple(SubmissionRefView.from_ref(ref) for ref in application.submission_refs),
            services=tuple(ServiceLineView.from_line(line) for line in application.service_lines),
            consents=tuple(ConsentView.from_consent(consent) for consent in application.consents),
            total_price=TotalPriceView.from_snapshot(total) if total is not None else None,
            status_history=tuple(ApplicationStatusChangeView.from_change(change) for change in application.status_history),
            payment_receipts=tuple(
                PaymentReceiptView(id=receipt.id.json(), file_reference=receipt.file.value, uploaded_at=receipt.uploaded_at)
                for receipt in application.payment_receipts
            ),
            paid_at=application.paid_at,
            created_at=application.created_at,
            updated_at=application.updated_at,
            version=application.version,
            editable=editable,
        )


@dataclass(frozen=True, slots=True)
class ApplicationSummaryView:
    """A compact read view of an application for listing screens."""

    id: str
    competition_id: str
    status: str
    has_corrections: bool
    submission_count: int
    total_amount: str | None
    currency: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_application(cls, application: Application) -> ApplicationSummaryView:
        total = application.total_price
        return cls(
            id=application.id.json(),
            competition_id=application.competition_id.json(),
            status=application.status.value,
            has_corrections=any(ref.status.value == "REQUIRES_CORRECTION" for ref in application.submission_refs),
            submission_count=application.submission_count,
            total_amount=str(total.total.amount) if total is not None else None,
            currency=total.total.currency.value if total is not None else None,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )


@dataclass(frozen=True, slots=True)
class ApplicationOperationResultDto:
    """The outcome of an order command: the affected application plus its events."""

    application: ApplicationView
    events: tuple[DomainEvent, ...]

    @classmethod
    def of(cls, application: Application, events: tuple[DomainEvent, ...]) -> ApplicationOperationResultDto:
        return cls(application=ApplicationView.from_application(application), events=events)
