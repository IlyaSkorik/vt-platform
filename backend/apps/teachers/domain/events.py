"""Domain events emitted by the Teacher Directory bounded context.

Past-tense **business facts** (ARCH-001 §4.8) about the ``Teacher`` aggregate. Pure
domain code: standard library only, no handlers/transport. Every event is a frozen,
slotted, keyword-only dataclass with a common envelope and a JSON-safe
:meth:`DomainEvent.to_dict`.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from .value_objects import OwnerId, TeacherRole, _generate_uuid7

__all__ = [
    "DomainEvent",
    "TeacherAdded",
    "TeacherArchived",
    "TeacherReactivated",
    "TeacherUpdated",
]


def _utcnow() -> datetime:
    """The current instant as a timezone-aware **UTC** datetime (default factory)."""
    return datetime.now(UTC)


def _serialize(value: object) -> object:
    """Render a single field value as a JSON-safe primitive."""
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
        case OwnerId():
            return value.json()
        case TeacherRole():
            return str(value)
    raise TypeError(f"Cannot serialize event field of type {type(value).__name__!r}.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Common, immutable envelope shared by every Teacher Directory domain event."""

    aggregate_id: uuid.UUID
    event_id: uuid.UUID = field(default_factory=_generate_uuid7)
    occurred_at: datetime = field(default_factory=_utcnow)
    event_version: int = 1

    def to_dict(self) -> dict[str, object]:
        """Render a JSON-safe payload with an ``event_type`` discriminator."""
        payload = {name: _serialize(getattr(self, name)) for name in (f.name for f in dataclasses.fields(self))}
        payload["event_type"] = type(self).__name__
        return payload


@dataclass(frozen=True, slots=True, kw_only=True)
class TeacherAdded(DomainEvent):
    """A teacher was added to a user's personal directory."""

    owner_id: OwnerId
    role: TeacherRole


@dataclass(frozen=True, slots=True, kw_only=True)
class TeacherUpdated(DomainEvent):
    """A teacher's details were updated."""


@dataclass(frozen=True, slots=True, kw_only=True)
class TeacherArchived(DomainEvent):
    """A teacher was archived (hidden from the directory, preserved)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class TeacherReactivated(DomainEvent):
    """An archived teacher was reactivated back into the directory."""
