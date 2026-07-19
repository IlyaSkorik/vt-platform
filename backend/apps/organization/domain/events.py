"""Domain events emitted by the Organization bounded context.

Past-tense **business facts** (ARCH-001 §4.8) — something already happened to an
aggregate; an event names it, timestamps it, and carries just enough data for a
consumer to react without reaching back into this context.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only. There are no
handlers, subscribers, dispatchers, or transport here — publishing is an outer-
layer concern; the domain only *produces* the fact. Every event is a frozen,
slotted, keyword-only dataclass: immutable, self-describing (via
:meth:`DomainEvent.to_dict`), and value-comparable.

Common envelope (:class:`DomainEvent`):

* ``event_id``      — unique **UUID v7** identity of this occurrence (dedup key).
* ``occurred_at``   — timezone-aware **UTC** instant the fact happened.
* ``aggregate_id``  — the UUID of the aggregate the fact is about.
* ``event_version`` — schema version of the payload, for evolution.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from .value_objects import (
    InvitationTokenHash,
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
    StaffEmail,
    StaffInvitationId,
    StaffMembershipId,
    StaffRole,
    StaffUserId,
    _generate_uuid7,
)

__all__ = [
    "DomainEvent",
    "OrganizationProfileUpdated",
    "OrganizationReactivated",
    "OrganizationRenamed",
    "OrganizationSeeded",
    "OrganizationSuspended",
    "StaffInvitationAccepted",
    "StaffInvitationIssued",
    "StaffInvitationRevoked",
    "StaffMembershipActivated",
    "StaffMembershipRevoked",
    "StaffMembershipRoleChanged",
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
        case OrganizationId() | StaffMembershipId() | StaffInvitationId() | StaffUserId():
            return value.json()
        case OrganizationName() | OrganizationSlug() | StaffEmail() | InvitationTokenHash():
            return str(value)
    raise TypeError(f"Cannot serialize event field of type {type(value).__name__!r}.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Common, immutable envelope shared by every Organization domain event."""

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
# Organization events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationSeeded(DomainEvent):
    """The singleton organization was seeded into existence."""

    name: OrganizationName
    slug: OrganizationSlug


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationSuspended(DomainEvent):
    """The organization was suspended (administrative break-glass)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationReactivated(DomainEvent):
    """A suspended organization was reactivated."""


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationProfileUpdated(DomainEvent):
    """The organization's public contact & legal profile was edited by staff."""


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationRenamed(DomainEvent):
    """The organization's display name was changed by staff."""

    name: OrganizationName


# ---------------------------------------------------------------------------
# StaffInvitation events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class StaffInvitationIssued(DomainEvent):
    """A staff invitation was issued to an email address for a role."""

    organization_id: OrganizationId
    email: StaffEmail
    role: StaffRole
    invited_by: StaffUserId
    expires_at: datetime
    raw_token: str


@dataclass(frozen=True, slots=True, kw_only=True)
class StaffInvitationAccepted(DomainEvent):
    """A staff invitation was accepted by a user."""

    organization_id: OrganizationId
    accepted_by: StaffUserId
    role: StaffRole


@dataclass(frozen=True, slots=True, kw_only=True)
class StaffInvitationRevoked(DomainEvent):
    """A pending staff invitation was revoked before acceptance."""

    organization_id: OrganizationId
    revoked_by: StaffUserId


# ---------------------------------------------------------------------------
# StaffMembership events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class StaffMembershipActivated(DomainEvent):
    """A staff membership became ACTIVE (invitation accepted or bootstrap owner)."""

    organization_id: OrganizationId
    user_id: StaffUserId
    role: StaffRole


@dataclass(frozen=True, slots=True, kw_only=True)
class StaffMembershipRoleChanged(DomainEvent):
    """An active staff membership's role was changed."""

    organization_id: OrganizationId
    user_id: StaffUserId
    old_role: StaffRole
    new_role: StaffRole
    changed_by: StaffUserId


@dataclass(frozen=True, slots=True, kw_only=True)
class StaffMembershipRevoked(DomainEvent):
    """An active staff membership was revoked (staff access removed)."""

    organization_id: OrganizationId
    user_id: StaffUserId
    revoked_by: StaffUserId
