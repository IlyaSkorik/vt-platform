"""Domain events emitted by the Applications (Competition Submission) bounded context.

Past-tense **business facts** (ARCH-001 §4.8) - something already happened to the
:class:`~apps.applications.domain.entities.Submission` aggregate; an event names
it, timestamps it, and carries just enough data for a consumer to react without
reaching back into this context.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only. There are no
handlers, subscribers, dispatchers, or transport here - publishing is an outer-
layer concern; the domain only *produces* the fact. Every event is a frozen,
slotted, keyword-only dataclass: immutable, self-describing (via
:meth:`DomainEvent.to_dict`), and value-comparable.

Only *meaningful* facts are events. The lifecycle milestones and the
composition of the submission (participants, teachers, attachments, price
snapshot, reviews) are events the future Scheduling / Judging / Finance contexts
will react to.

Common envelope (:class:`DomainEvent`):

* ``event_id``      - unique **UUID v7** identity of this occurrence (dedup key).
* ``occurred_at``   - timezone-aware **UTC** instant the fact happened.
* ``aggregate_id``  - the UUID of the aggregate the fact is about.
* ``event_version`` - schema version of the payload, for evolution.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from .value_objects import (
    ApplicationStatus,
    AttachmentId,
    AttachmentType,
    CompetitionId,
    Currency,
    EducationalOrganizationId,
    ParticipantId,
    PaymentReceiptId,
    ReviewerId,
    ReviewId,
    ServiceId,
    SubmissionId,
    SubmissionStatus,
    TeacherId,
    TeacherRole,
    UserId,
    _generate_uuid7,
)

__all__ = [
    "AdditionalServiceRemoved",
    "AdditionalServiceSelected",
    "ApplicationAwaitingPayment",
    "ApplicationCancelled",
    "ApplicationCompleted",
    "ApplicationCreated",
    "ApplicationPaid",
    "ApplicationSubmitted",
    "AttachmentAdded",
    "AttachmentRemoved",
    "ConsentsRecorded",
    "DomainEvent",
    "EducationalOrganizationSelected",
    "ParticipantAdded",
    "ParticipantMembersChanged",
    "ParticipantRemoved",
    "PaymentReceiptRemoved",
    "PaymentReceiptUploaded",
    "PerformanceDefined",
    "PriceSnapshotCreated",
    "ReviewAdded",
    "SubmissionAccepted",
    "SubmissionApproved",
    "SubmissionAttachedToApplication",
    "SubmissionAwaitingPayment",
    "SubmissionCancelled",
    "SubmissionCompleted",
    "SubmissionCreated",
    "SubmissionDetachedFromApplication",
    "SubmissionPaid",
    "SubmissionReturnedForCorrection",
    "SubmissionReviewStarted",
    "SubmissionScheduled",
    "SubmissionSubmitted",
    "TeacherAdded",
    "TeacherRemoved",
]


def _utcnow() -> datetime:
    """The current instant as a timezone-aware **UTC** datetime (default factory)."""
    return datetime.now(UTC)


def _serialize(value: object) -> object:
    """Render a single field value as a JSON-safe primitive.

    Maps domain value objects and stdlib temporal/identity types to strings;
    plain scalars pass through. Raises :class:`TypeError` on anything unmapped so
    a non-serializable payload fails loudly rather than silently producing junk.
    """
    match value:
        case None:
            return None
        case StrEnum():
            return value.value
        case bool() | int() | float() | str():
            return value
        case datetime():
            return value.isoformat()
        case uuid.UUID():
            return str(value)
        case (
            CompetitionId()
            | UserId()
            | ReviewerId()
            | ParticipantId()
            | TeacherId()
            | AttachmentId()
            | ReviewId()
            | SubmissionId()
            | EducationalOrganizationId()
            | ServiceId()
        ):
            return value.json()
        case TeacherRole():
            return str(value)
    raise TypeError(f"Cannot serialize event field of type {type(value).__name__!r}.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Common, immutable envelope shared by every Applications domain event."""

    aggregate_id: uuid.UUID
    event_id: uuid.UUID = field(default_factory=_generate_uuid7)
    occurred_at: datetime = field(default_factory=_utcnow)
    event_version: int = 1

    def to_dict(self) -> dict[str, object]:
        """Render a JSON-safe payload with an ``event_type`` discriminator.

        Every dataclass field is serialized via :func:`_serialize`; the concrete
        event's class name is added as ``event_type`` so a consumer (outbox, log,
        wire) can route without importing the class.
        """
        payload = {name: _serialize(getattr(self, name)) for name in (f.name for f in dataclasses.fields(self))}
        payload["event_type"] = type(self).__name__
        return payload


# ---------------------------------------------------------------------------
# Composition events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionCreated(DomainEvent):
    """A submission was created as a DRAFT by an applicant for a competition."""

    competition_id: CompetitionId
    applicant_id: UserId


@dataclass(frozen=True, slots=True, kw_only=True)
class PerformanceDefined(DomainEvent):
    """The submission's single performance was set or replaced."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipantAdded(DomainEvent):
    """A participant was added to the submission."""

    participant_id: ParticipantId


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipantMembersChanged(DomainEvent):
    """A collective's roster of named members was replaced (possibly emptied).

    Its own event rather than a re-used ``ParticipantAdded``: the roster is what asks
    for an individual document per person, so "who is named on this entry" is a fact
    worth reading back out of the stream on its own.
    """

    participant_id: ParticipantId


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipantRemoved(DomainEvent):
    """A participant was removed from the submission."""

    participant_id: ParticipantId


@dataclass(frozen=True, slots=True, kw_only=True)
class TeacherAdded(DomainEvent):
    """A teacher was added to the submission."""

    teacher_id: TeacherId
    role: TeacherRole


@dataclass(frozen=True, slots=True, kw_only=True)
class TeacherRemoved(DomainEvent):
    """A teacher was removed from the submission."""

    teacher_id: TeacherId


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentAdded(DomainEvent):
    """An attachment reference was added to the submission."""

    attachment_id: AttachmentId
    attachment_type: AttachmentType


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentRemoved(DomainEvent):
    """An attachment reference was removed from the submission."""

    attachment_id: AttachmentId


@dataclass(frozen=True, slots=True, kw_only=True)
class PriceSnapshotCreated(DomainEvent):
    """An immutable price snapshot was frozen onto the submission."""

    amount: str
    currency: Currency
    calculated_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewAdded(DomainEvent):
    """An organizer review iteration was recorded on the submission."""

    review_id: ReviewId
    reviewer_id: ReviewerId


# ---------------------------------------------------------------------------
# Lifecycle events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionSubmitted(DomainEvent):
    """The submission was submitted to the competition (left DRAFT/correction)."""

    previous_status: SubmissionStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionReviewStarted(DomainEvent):
    """The organizer began reviewing the submission."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionReturnedForCorrection(DomainEvent):
    """The submission was returned to the applicant for correction."""

    review_id: ReviewId


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionApproved(DomainEvent):
    """The submission was approved by the organizer."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionAwaitingPayment(DomainEvent):
    """The submission is approved and awaiting payment."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionPaid(DomainEvent):
    """The submission's fee was paid."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionAccepted(DomainEvent):
    """The submission was accepted into the competition (content now frozen)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionScheduled(DomainEvent):
    """The submission was assigned a slot in the running order."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionCompleted(DomainEvent):
    """The submission's performance took place."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionCancelled(DomainEvent):
    """The submission was cancelled (withdrawn or rejected)."""

    previous_status: SubmissionStatus


# ===========================================================================
# Application aggregate (order-level) events
# ===========================================================================
#
# Facts about the sibling :class:`~apps.applications.domain.entities.Application`
# aggregate - the order grouping one applicant's Submissions for one competition.
# The ``aggregate_id`` on these events is the ``ApplicationId``.


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationCreated(DomainEvent):
    """An application (order) was created as a DRAFT by an applicant for a competition."""

    competition_id: CompetitionId
    applicant_id: UserId


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionAttachedToApplication(DomainEvent):
    """A submission was attached to the application (a performance added to the order)."""

    submission_id: SubmissionId


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmissionDetachedFromApplication(DomainEvent):
    """A submission reference was removed from the application (while still a draft)."""

    submission_id: SubmissionId


@dataclass(frozen=True, slots=True, kw_only=True)
class EducationalOrganizationSelected(DomainEvent):
    """The applicant selected the educational organization for the application."""

    educational_organization_id: EducationalOrganizationId


@dataclass(frozen=True, slots=True, kw_only=True)
class AdditionalServiceSelected(DomainEvent):
    """An additional service was selected on the application."""

    service_id: ServiceId


@dataclass(frozen=True, slots=True, kw_only=True)
class AdditionalServiceRemoved(DomainEvent):
    """An additional service was removed from the application."""

    service_id: ServiceId


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsentsRecorded(DomainEvent):
    """The set of accepted consents was recorded on the application."""

    consent_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationSubmitted(DomainEvent):
    """The application (order) was submitted; its total price was frozen."""

    amount: str
    currency: Currency


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationAwaitingPayment(DomainEvent):
    """All referenced submissions are approved; the application awaits payment."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationPaid(DomainEvent):
    """The application's total was paid."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationCompleted(DomainEvent):
    """The application (order) was fully settled."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationCancelled(DomainEvent):
    """The application (order) was cancelled (withdrawn or rejected)."""

    previous_status: ApplicationStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentReceiptUploaded(DomainEvent):
    """The applicant attached one more payment receipt to the order."""

    receipt_id: PaymentReceiptId


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentReceiptRemoved(DomainEvent):
    """The applicant detached one of the order's payment receipts."""

    receipt_id: PaymentReceiptId
