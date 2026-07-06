"""Domain events emitted by the Identity & Access bounded context.

Past-tense **business facts** — the integration currency between bounded
contexts (ARCH-001 §4.8, DATA-003). Something already happened to a user
aggregate; an event names it, timestamps it, and carries just enough business
data for a consumer to react without reaching back into this context.

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
* ``aggregate_id``  — the :class:`UserId` the fact is about.
* ``event_version`` — schema version of the event's payload, for evolution.

Events implemented here (all past tense — they report, never command):

* :class:`UserRegistered`          — a new account was created.
* :class:`EmailVerified`           — an email address was confirmed.
* :class:`PhoneVerified`           — a phone number was confirmed.
* :class:`PasswordChanged`         — an authenticated user changed their password.
* :class:`PasswordResetRequested`  — a password reset was initiated.
* :class:`PasswordResetCompleted`  — a password reset flow finished.
* :class:`ConsentGranted`          — the user accepted a versioned consent document.
* :class:`ConsentWithdrawn`        — the user revoked a previously granted consent.
* :class:`RoleAssigned`            — a role was granted to the user.
* :class:`RoleRevoked`             — a role was removed from the user.
* :class:`UserLocked`              — the account was locked out.
* :class:`UserUnlocked`            — the account lock was released.
* :class:`SessionStarted`          — an authenticated session was opened.
* :class:`SessionEnded`            — an authenticated session was closed.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

from .value_objects import (
    ConsentVersion,
    Email,
    FullName,
    Locale,
    PhoneNumber,
    Timezone,
    UserId,
    _generate_uuid7,
)

__all__ = [
    "ConsentGranted",
    "ConsentType",
    "ConsentWithdrawn",
    "DomainEvent",
    "EmailVerified",
    "PasswordChanged",
    "PasswordResetCompleted",
    "PasswordResetRequested",
    "PhoneVerified",
    "RoleAssigned",
    "RoleRevoked",
    "SessionEndReason",
    "SessionEnded",
    "SessionStarted",
    "UserLocked",
    "UserRegistered",
    "UserUnlocked",
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
# Enumerations (self-documenting classifiers carried by some events)
# ---------------------------------------------------------------------------


class ConsentType(StrEnum):
    """The kind of consent a :class:`ConsentGranted`/:class:`ConsentWithdrawn` is about.

    A :class:`~enum.StrEnum`, so each member *is* its wire value and serializes to a
    plain string with no extra handling. The set reflects the legal bases the
    platform tracks for a children's competition service (DATA-001 §4.1): the minor
    data-processing consent is distinct from the general one because a guardian, not
    the child, grants it.
    """

    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    DATA_PROCESSING = "data_processing"
    MINOR_DATA_PROCESSING = "minor_data_processing"
    MARKETING = "marketing"


class SessionEndReason(StrEnum):
    """Why a :class:`SessionEnded` occurred.

    Distinguishes a deliberate logout from an expiry or a forced revocation so a
    consumer (audit trail, security analytics) can react differently — e.g. a
    ``REVOKED`` or ``ADMIN_TERMINATED`` end is security-relevant, a plain
    ``LOGOUT`` is not.
    """

    LOGOUT = "logout"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PASSWORD_CHANGED = "password_changed"
    ADMIN_TERMINATED = "admin_terminated"


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------


def _serialize(value: object) -> object:
    """Render a single field value as a JSON-safe primitive.

    Keeps :meth:`DomainEvent.to_dict` generic: domain value objects and stdlib
    temporal/identity types are mapped to strings (or, for :class:`FullName`, a
    structured dict that preserves every part), while plain scalars pass through.
    Raises :class:`TypeError` on anything unmapped so an accidentally
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
        case UserId():
            return value.json()
        case FullName():
            return {
                "first_name": value.first_name,
                "last_name": value.last_name,
                "middle_name": value.middle_name,
            }
        case Email() | PhoneNumber() | ConsentVersion() | Locale() | Timezone():
            return str(value)
    raise TypeError(f"Cannot serialize event field of type {type(value).__name__!r}.")


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Common, immutable envelope shared by every Identity domain event.

    A recorded fact, not a request: it is past tense, cannot be mutated, and
    carries the four fields every consumer needs regardless of the concrete event.
    Subclasses add only their specific **business** payload.

    Fields are **keyword-only** so the envelope defaults (``event_id``,
    ``occurred_at``, ``event_version``) can precede a subclass's required business
    fields without the "non-default argument follows default argument" clash, and
    so every call site reads self-documentingly (``UserRegistered(aggregate_id=…,
    email=…)``). ``event_id`` and ``occurred_at`` default to a fresh UUID v7 and
    the current UTC instant, so the normal path is simply to pass the business
    data; both may still be supplied explicitly when reconstructing a known event.

    Invariants (validated on construction):

    * ``event_id`` is a UUID **v7** — time-ordered and globally unique, giving
      consumers a natural dedup/idempotency key.
    * ``occurred_at`` is timezone-aware and normalized to **UTC**.
    * ``event_version`` is a positive integer.
    """

    aggregate_id: UserId
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
        for an outbox row, a structured log, or the wire — the transport itself
        stays in an outer layer.
        """
        payload: dict[str, object] = {"event_type": self.event_type}
        for spec in dataclasses.fields(self):
            payload[spec.name] = _serialize(getattr(self, spec.name))
        return payload


# ---------------------------------------------------------------------------
# Registration & contact verification
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRegistered(DomainEvent):
    """A new user account was created (IDN-001).

    The genesis fact of the aggregate. Consumers key onboarding off this: send the
    verification email, provision defaults, seed analytics. Carries the initial
    contact address, the person's name, and the chosen interface locale so a
    welcome flow needs nothing beyond the event. The email is **not** verified yet
    — that is announced separately by :class:`EmailVerified`.
    """

    email: Email
    full_name: FullName
    locale: Locale


@dataclass(frozen=True, slots=True, kw_only=True)
class EmailVerified(DomainEvent):
    """A user confirmed ownership of an email address (IDN-002).

    Flips the address from claimed to trusted, unlocking flows that require a
    reachable mailbox (password reset, transactional notifications). Carries the
    exact address verified, since an account may change it over its lifetime.
    """

    email: Email


@dataclass(frozen=True, slots=True, kw_only=True)
class PhoneVerified(DomainEvent):
    """A user confirmed ownership of a phone number (IDN-002).

    The SMS/telephony analogue of :class:`EmailVerified`; enables channels that
    depend on a reachable number. Carries the exact E.164 number verified.
    """

    phone: PhoneNumber


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class PasswordChanged(DomainEvent):
    """An authenticated user changed their own password (IDN-003).

    Deliberately carries no payload beyond the envelope: the *fact* that the
    credential rotated at a given instant is the whole point, and the digest itself
    never belongs in an event. Security consumers react by, e.g., ending other
    sessions (see :class:`SessionEndReason.PASSWORD_CHANGED`); the notification of
    which address to alert is resolved from ``aggregate_id`` in the outer layer.
    Distinct from the reset flow (:class:`PasswordResetCompleted`), which starts
    from an unauthenticated request.
    """


@dataclass(frozen=True, slots=True, kw_only=True)
class PasswordResetRequested(DomainEvent):
    """A password reset was initiated for an account (IDN-004).

    Announces intent, not completion. Carries the ``email`` the reset link is sent
    to and the ``expires_at`` deadline after which the flow is void — enough for a
    consumer to deliver the message and for auditing the request window. It
    deliberately carries **no** token/secret: credentials never travel in an event.
    """

    email: Email
    expires_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class PasswordResetCompleted(DomainEvent):
    """A password reset flow finished and a new password is in effect (IDN-004).

    The terminal fact of the reset started by :class:`PasswordResetRequested`.
    Carries the ``email`` so a "your password was changed" confirmation can be sent
    without a lookup. Like :class:`PasswordChanged`, security consumers may use it
    to invalidate outstanding sessions.
    """

    email: Email


# ---------------------------------------------------------------------------
# Consent (DATA-001 §4.1, IDN-005)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsentGranted(DomainEvent):
    """The user accepted a specific, versioned consent document (IDN-005).

    Consent is legal evidence and is always tied to the exact text version in force
    (DATA-001 §4.1), so the event records both *what* was consented to
    (``consent_type``) and *which version* (``consent_version``). This pairing lets
    the platform later answer "did they accept the current version?" and re-prompt
    when a newer one ships.
    """

    consent_type: ConsentType
    consent_version: ConsentVersion


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsentWithdrawn(DomainEvent):
    """The user revoked a previously granted consent (IDN-005).

    The inverse of :class:`ConsentGranted`. Records the ``consent_version`` that was
    in force at withdrawal so the audit trail is unambiguous. Withdrawal may cascade
    (e.g. revoking data-processing consent restricts what the platform may retain);
    acting on that is an outer-layer policy, not this fact.
    """

    consent_type: ConsentType
    consent_version: ConsentVersion


# ---------------------------------------------------------------------------
# Roles & access
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class RoleAssigned(DomainEvent):
    """A role was granted to the user (IDN-006).

    Widens what the account may do (participant, guardian, judge, organizer, …).
    ``role`` is the role identifier; ``assigned_by`` records the actor who granted
    it — ``None`` when the platform assigned it automatically (e.g. a default role
    at registration) rather than an administrator. The audit trail cares who
    escalated access, hence the actor is part of the fact.
    """

    role: str
    assigned_by: UserId | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RoleRevoked(DomainEvent):
    """A role was removed from the user (IDN-006).

    The inverse of :class:`RoleAssigned`; narrows the account's access.
    ``revoked_by`` records the actor, or ``None`` for a system/automatic revocation.
    """

    role: str
    revoked_by: UserId | None = None


# ---------------------------------------------------------------------------
# Account lockout
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class UserLocked(DomainEvent):
    """The account was locked and can no longer authenticate (IDN-007).

    Raised for security (too many failed attempts) or administratively. ``reason``
    is a short, human-readable cause for the audit trail. ``locked_until`` bounds a
    *temporary* lock (e.g. a cool-off after failed logins); ``None`` means the lock
    is indefinite until an explicit :class:`UserUnlocked`.
    """

    reason: str
    locked_until: datetime | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UserUnlocked(DomainEvent):
    """A previously locked account was restored to normal use (IDN-007).

    The inverse of :class:`UserLocked`, whether triggered by an administrator or by
    a temporary lock's ``locked_until`` elapsing. ``reason`` records why the lock
    was released.
    """

    reason: str


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionStarted(DomainEvent):
    """An authenticated session was opened for the user (IDN-008).

    Emitted on successful login / token issuance. ``session_id`` identifies the
    session so it can be correlated with the eventual :class:`SessionEnded`.
    ``ip_address`` and ``user_agent`` are optional security context for anomaly
    detection and the "your active sessions" surface; both are ``None`` when a
    channel does not supply them.
    """

    session_id: uuid.UUID
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionEnded(DomainEvent):
    """An authenticated session was closed (IDN-008).

    Closes the session opened by :class:`SessionStarted` (matched on
    ``session_id``). ``reason`` (a :class:`SessionEndReason`) distinguishes a
    deliberate logout from an expiry or a forced revocation, which is exactly what a
    security consumer needs to decide whether the end is noteworthy.
    """

    session_id: uuid.UUID
    reason: SessionEndReason
