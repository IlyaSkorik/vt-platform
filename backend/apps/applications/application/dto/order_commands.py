"""Command DTOs for the Application (order) use cases.

Framework-neutral, frozen, slotted request payloads carrying only primitives -
never domain value objects and never behaviour. ``requested_by`` is the acting
user's id (the order owner); handlers enforce ownership. Instants the domain needs
are resolved by the handler's clock, not carried here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "AddSubmissionToApplicationCommand",
    "CancelApplicationCommand",
    "CompleteApplicationCommand",
    "ConsentInput",
    "CreateApplicationCommand",
    "MarkApplicationPaidCommand",
    "RecordConsentsCommand",
    "RemoveAdditionalServiceCommand",
    "RemoveSubmissionFromApplicationCommand",
    "RequestApplicationPaymentCommand",
    "SelectAdditionalServiceCommand",
    "SelectEducationalOrganizationCommand",
    "SubmitApplicationCommand",
    "SyncApplicationCommand",
    "UploadApplicationReceiptCommand",
]


@dataclass(frozen=True, slots=True)
class CreateApplicationCommand:
    """Create a new DRAFT application (order) for a competition."""

    requested_by: str
    competition_id: str


@dataclass(frozen=True, slots=True)
class AddSubmissionToApplicationCommand:
    """Create a fresh draft submission within the application and attach it."""

    requested_by: str
    application_id: str


@dataclass(frozen=True, slots=True)
class RemoveSubmissionFromApplicationCommand:
    """Detach a submission from the application (and cancel it - never a hard delete)."""

    requested_by: str
    application_id: str
    submission_id: str


@dataclass(frozen=True, slots=True)
class SelectAdditionalServiceCommand:
    """Select a competition additional service on the application."""

    requested_by: str
    application_id: str
    service_id: str
    quantity: int = 1


@dataclass(frozen=True, slots=True)
class RemoveAdditionalServiceCommand:
    """Remove a previously selected additional service from the application."""

    requested_by: str
    application_id: str
    service_id: str


@dataclass(frozen=True, slots=True)
class ConsentInput:
    """One accepted consent carried in a command (code + accepted text version)."""

    code: str
    version: str


@dataclass(frozen=True, slots=True)
class RecordConsentsCommand:
    """Record the set of accepted consents on the application."""

    requested_by: str
    application_id: str
    consents: tuple[ConsentInput, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SelectEducationalOrganizationCommand:
    """Select the applicant's educational organization for the application."""

    requested_by: str
    application_id: str
    educational_organization_id: str


@dataclass(frozen=True, slots=True)
class SubmitApplicationCommand:
    """Submit the order: submit each attached submission, then place the order."""

    requested_by: str
    application_id: str


@dataclass(frozen=True, slots=True)
class RequestApplicationPaymentCommand:
    """Move the order to awaiting payment (requires all submissions approved)."""

    requested_by: str
    application_id: str


@dataclass(frozen=True, slots=True)
class MarkApplicationPaidCommand:
    """Record that the order's total was paid (and accept its approved submissions)."""

    requested_by: str
    application_id: str


@dataclass(frozen=True, slots=True)
class CompleteApplicationCommand:
    """Mark the order as fully settled."""

    requested_by: str
    application_id: str


@dataclass(frozen=True, slots=True)
class CancelApplicationCommand:
    """Cancel the order (and cancel its non-terminal submissions)."""

    requested_by: str
    application_id: str


@dataclass(frozen=True, slots=True)
class SyncApplicationCommand:
    """Refresh the cached submission snapshots on the order from live submissions."""

    requested_by: str
    application_id: str


@dataclass(frozen=True, slots=True)
class UploadApplicationReceiptCommand:
    """Upload (or replace) the applicant's payment receipt for the whole order.

    Carries the raw uploaded bytes plus its declared filename and content type; the
    handler validates them against the fixed receipt constraints, stores the bytes,
    and attaches the resulting reference to the order.
    """

    requested_by: str
    application_id: str
    filename: str
    content_type: str
    content: bytes
