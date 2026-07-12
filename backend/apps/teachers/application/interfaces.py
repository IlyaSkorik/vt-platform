"""Application ports (contracts) required by Teacher Directory use cases.

The **outbound dependencies** of the Teacher Directory application layer, expressed
as pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion).
Concrete adapters (a Django ORM repository, a clock, a UUID source, an event
publisher) live in ``infrastructure/`` and are injected at composition time; the
dependency arrow points inward.

**Framework-free** (ARCH-001 §4.1, §7.2): standard library and this context's
domain only. Interfaces only, no implementations.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.teachers.domain.entities import Teacher
from apps.teachers.domain.events import DomainEvent
from apps.teachers.domain.value_objects import OwnerId, TeacherId

__all__ = [
    "Clock",
    "EventPublisher",
    "TeacherRepository",
    "UuidGenerator",
]


@runtime_checkable
class TeacherRepository(Protocol):
    """Port: persistence & retrieval of the :class:`Teacher` aggregate.

    Loads and saves whole aggregates, honouring the root's optimistic-concurrency
    ``version``. Getters report absence as ``None``. Listing is scoped to an owner
    (a personal directory), optionally including archived entries.
    """

    def get(self, teacher_id: TeacherId) -> Teacher | None:
        """Return the teacher with ``teacher_id`` (any state), or ``None``."""
        ...

    def list_for_owner(self, owner_id: OwnerId, *, include_archived: bool = False) -> Sequence[Teacher]:
        """Return the owner's directory entries, newest first, optionally with archived ones."""
        ...

    def save(self, teacher: Teacher) -> None:
        """Persist ``teacher`` (insert or update), honouring its optimistic version."""
        ...


@runtime_checkable
class Clock(Protocol):
    """Port: the current instant, injected rather than read globally."""

    def now(self) -> datetime:
        """The current instant as a timezone-aware datetime (possibly non-UTC)."""
        ...

    def utcnow(self) -> datetime:
        """The current instant as a timezone-aware **UTC** datetime."""
        ...


@runtime_checkable
class UuidGenerator(Protocol):
    """Port: source of fresh UUID v7 identifiers, injected rather than read globally."""

    def new(self) -> uuid.UUID:
        """Return a brand-new time-ordered UUID version 7."""
        ...


@runtime_checkable
class EventPublisher(Protocol):
    """Port: dispatch recorded domain events to the world outside the aggregate."""

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Publish ``events`` in order to the platform's event transport."""
        ...
