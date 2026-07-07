"""Domain events emitted by the Participants bounded context.

Past-tense **business facts** — the integration currency between bounded
contexts (ARCH-001 §4.8, DATA-003 §4.2). Something already happened to a
Participant aggregate; an event names it, timestamps it, and carries just enough
business data for a consumer to react without reaching back into this context.

This is **pure domain code** (ARCH-001 §4.1, §7.2): standard library only — no
Django, no DRF, no ORM, no message bus, no Celery/Kafka. There are deliberately
**no** handlers, subscribers, dispatchers, or transport here. Publishing an event
(assigning it a bus, a topic, an outbox row) is an outer-layer concern
(``application``/``infrastructure``); the domain only *produces* the fact.

Every event is a frozen, slotted, keyword-only dataclass, so an instance is:

* **immutable** — a recorded fact never changes after it happened;
* **self-describing** — :meth:`DomainEvent.to_dict` renders a JSON-safe payload
  (with an ``event_type`` discriminator) for an outbox, a log line, or the wire;
* **value-comparable** — two events with the same fields are equal.

Common envelope, carried by every event (:class:`DomainEvent`):

* ``event_id``      — unique **UUID v7** identity of *this occurrence* (dedup key).
* ``occurred_at``   — timezone-aware **UTC** instant the fact happened.
* ``aggregate_id``  — the :class:`ParticipantId` the fact is about.
* ``event_version`` — schema version of the event's payload, for evolution.

Events implemented here (all past tense — they report, never command):

* :class:`ParticipantCreated`          — EVT-PRT-001: a participant record was created.
* :class:`GuardianLinked`              — EVT-PRT-002: a verified guardian relationship exists.
* :class:`ParticipantVerified`         — EVT-PRT-003: a participant's details were verified.
* :class:`ParticipantActivated`        — EVT-PRT-004: a participant became active.
* :class:`ParticipantArchived`         — EVT-PRT-005: a participant was archived.
* :class:`ParticipantErasureRequested` — EVT-PRT-006: erasure of a participant was requested.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

from .value_objects import (
    ActorReference,
    AgeGroup,
    ConsentReference,
    DateOfBirth,
    DisplayAlias,
    GuardianId,
    GuardianRelationshipType,
    InstitutionId,
    ParticipantId,
    PersonName,
    TeacherId,
    _generate_uuid7,
)

__all__ = [
    "DomainEvent",
    "GuardianLinked",
    "ParticipantActivated",
    "ParticipantArchived",
    "ParticipantCreated",
    "ParticipantErasureRequested",
    "ParticipantVerified",
]

_UUID_V7_VERSION: Final = 7


def _utcnow() -> datetime:
    """The current instant as a timezone-aware **UTC** datetime.

    Default factory for :attr:`DomainEvent.occurred_at`. Aware (never naive) so a
    recorded fact can never be mixed up with a local wall-clock time, matching the
    platform's UTC storage rule (API-000 §22).
    """
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------


def _serialize(value: object) -> object:
    """Render a single field value as a JSON-safe primitive.

    Keeps :meth:`DomainEvent.to_dict` generic: domain value objects and stdlib
    temporal/identity types are mapped to strings (or, for structured values like
    :class:`PersonName`, a dict that preserves every part), while plain scalars
    pass through. Raises :class:`TypeError` on anything unmapped so an accidentally
    non-serializable payload fails loudly at construction of the dict rather than
    silently producing junk on the wire.
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
        case ParticipantId() | GuardianId() | TeacherId() | InstitutionId():
            return value.json()
        case PersonName():
            return {
                "first_name": value.first_name,
                "last_name": value.last_name,
                "middle_name": value.middle_name,
            }
        case ActorReference():
            return {"actor_id": str(value.actor_id), "actor_type": value.actor_type.value}
        case ConsentReference():
            return {"consent_id": str(value.consent_id), "consent_version": value.consent_version}
        case AgeGroup():
            return {
                "code": value.code,
                "label": value.label,
                "min_age": value.min_age,
                "max_age": value.max_age,
            }
        case DateOfBirth() | DisplayAlias():
            return str(value)
    raise TypeError(f"Cannot serialize event field of type {type(value).__name__!r}.")


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Common, immutable envelope shared by every Participants domain event.

    A recorded fact, not a request: it is past tense, cannot be mutated, and
    carries the four fields every consumer needs regardless of the concrete event.
    Subclasses add only their specific **business** payload.

    Fields are **keyword-only** so the envelope defaults (``event_id``,
    ``occurred_at``, ``event_version``) can precede a subclass's required business
    fields without the "non-default argument follows default argument" clash.
    ``event_id`` and ``occurred_at`` default to a fresh UUID v7 and the current UTC
    instant, so the normal path is simply to pass the business data; both may still
    be supplied explicitly when reconstructing a known event.

    Invariants (validated on construction):

    * ``event_id`` is a UUID **v7** — time-ordered and globally unique, giving
      consumers a natural dedup/idempotency key.
    * ``occurred_at`` is timezone-aware and normalized to **UTC**.
    * ``event_version`` is a positive integer.
    """

    aggregate_id: ParticipantId
    event_id: uuid.UUID = field(default_factory=_generate_uuid7)
    occurred_at: datetime = field(default_factory=_utcnow)
    event_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, uuid.UUID):  # defensive: wrong type
            raise TypeError(f"event_id must be a uuid.UUID, got {type(self.event_id).__name__!r}.")
        if self.event_id.version != _UUID_V7_VERSION:
            raise ValueError(f"event_id must be a UUID v7, got version {self.event_id.version}.")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be a timezone-aware datetime.")
        if self.event_version < 1:
            raise ValueError(f"event_version must be a positive integer, got {self.event_version}.")
        # Normalize to UTC so equality and the serialized form are canonical
        # regardless of the caller's zone (idempotent when already UTC).
        object.__setattr__(self, "occurred_at", self.occurred_at.astimezone(UTC))

    @property
    def event_type(self) -> str:
        """The concrete event's name — the discriminator used to route/deserialize."""
        return type(self).__name__

    def to_dict(self) -> dict[str, object]:
        """Render a JSON-safe payload of the whole event, business data included.

        The single serialization entry point: it walks the dataclass fields
        generically, converts value objects and temporal/identity types to
        primitives (see :func:`_serialize`), and prepends an ``event_type``
        discriminator so a consumer can tell which event a payload represents. The
        result contains only built-in types, so it is directly ``json.dumps``-able
        for an outbox row, a structured log, or the wire.
        """
        payload: dict[str, object] = {"event_type": self.event_type}
        for spec in dataclasses.fields(self):
            payload[spec.name] = _serialize(getattr(self, spec.name))
        return payload


# ---------------------------------------------------------------------------
# Lifecycle & relationship events (DATA-003 §4.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipantCreated(DomainEvent):
    """A participant (child) record was created under a guardian/teacher (EVT-PRT-001).

    The genesis fact of the aggregate. A child is being *prepared* for
    participation but is not yet active (activation waits on verified guardianship
    and consent, PRT-001). Carries the minimized profile facts, the date of birth
    used for age derivation (PRT-002), the pseudonymized alias, and the creating
    actor for the audit trail.
    """

    name: PersonName
    date_of_birth: DateOfBirth
    display_alias: DisplayAlias
    created_by: ActorReference


@dataclass(frozen=True, slots=True, kw_only=True)
class GuardianLinked(DomainEvent):
    """A verified guardian relationship to a participant was established (EVT-PRT-002).

    The responsible-adult link that enables consent and management now exists
    (PRT-001, PRT-003). Consumers in Identity treat the guardian as authorized to
    grant consent for this participant. Carries the guardian's identity and the
    relationship type; the established time is the envelope ``occurred_at``.
    """

    guardian_id: GuardianId
    relationship_type: GuardianRelationshipType


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipantVerified(DomainEvent):
    """A participant's required details were verified (EVT-PRT-003).

    One prerequisite toward activation is met (PRT-002): the minimized details and
    a valid date of birth are present. The participant is eligible for activation
    once guardianship/authority and active consent also exist.
    """


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipantActivated(DomainEvent):
    """A participant became active and may enter competitions (EVT-PRT-004).

    All activation preconditions are satisfied — verified guardianship or an
    authorized institution/teacher link, plus an active matching consent (PRT-001).
    Consumers (Applications) may now create applications for this participant.
    """


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipantArchived(DomainEvent):
    """A participant was archived — inactive, history preserved (EVT-PRT-005).

    Distinct from erasure (PRT-007): the child is no longer actively participating,
    but the record is retained per policy and may be reactivated subject to valid
    consent (DATA-004 §4.3).
    """


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipantErasureRequested(DomainEvent):
    """Erasure of a participant's personal data was requested (EVT-PRT-006).

    Triggers the privacy-critical erasure cascade (PRT-007): downstream
    performances/media are removed per the retention policy while financial/audit
    records are retained under an independent lawful basis (FIN-008). Carries the
    originating request reference (a DSAR or consent-withdrawal id) for the audit
    trail.
    """

    request_reference: uuid.UUID
