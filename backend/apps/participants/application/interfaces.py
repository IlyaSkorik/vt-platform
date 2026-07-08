"""Application ports (contracts) required by Participants use cases.

The **outbound dependencies** of the Participants application layer, expressed as
pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion). A use
case (command/query handler) depends only on these abstractions; the concrete
adapters — a Django ORM repository, a UUID v7 generator, an outbox publisher —
live in ``infrastructure/`` and are injected at composition time. The dependency
arrow therefore points *inward*: infrastructure depends on this module, never the
reverse.

This module is **framework-free** (ARCH-001 §4.1, §7.2): standard library only —
no Django, no DRF, no ORM, no message bus, no IO. It contains **interfaces only**;
there are deliberately no implementations here. Every method is fully typed and no
signature uses ``Any``.

Design choices worth stating once, since they shape every port below:

* **Protocols, not ABCs.** Structural typing lets an adapter satisfy a port
  without importing or inheriting from it, keeping the core free of outward edges.
  The protocols are :func:`~typing.runtime_checkable` purely so tests can assert
  conformance with ``isinstance``.
* **Lookups return ``Participant | None``.** The getters report absence as
  ``None`` rather than raising, so the *use case* decides whether a missing
  participant is an error. The companion ``exists_*`` methods answer presence
  questions without materializing an aggregate.
* **Time and identity are injected.** :class:`Clock` and :class:`UuidGenerator`
  exist so use cases never call ``datetime.now`` or ``uuid`` directly, keeping
  them deterministic and testable.

Ports defined here:

* :class:`ParticipantRepository` — persistence & retrieval of the ``Participant`` aggregate.
* :class:`Clock`                 — the current instant, injected not read globally.
* :class:`UuidGenerator`         — fresh UUID v7 identifiers, injected not read globally.
* :class:`EventPublisher`        — dispatch of recorded domain events to the outside.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.participants.domain.entities import Participant
from apps.participants.domain.events import DomainEvent
from apps.participants.domain.value_objects import DisplayAlias, ParticipantId

__all__ = [
    "Clock",
    "EventPublisher",
    "ParticipantRepository",
    "UuidGenerator",
]


# ---------------------------------------------------------------------------
# Repository port
# ---------------------------------------------------------------------------


@runtime_checkable
class ParticipantRepository(Protocol):
    """Port: persistence and retrieval of the :class:`Participant` aggregate root.

    **Why it exists.** Use cases must load and store participants without knowing
    *how* they are stored. This port is the seam that inverts that dependency: the
    application layer speaks only ``Participant`` and value objects, never SQL, an
    ORM model, or a session.

    **Who implements it.** An adapter in ``apps.participants.infrastructure`` backed
    by the Django ORM (mapping the aggregate and its guardian-link rows to/from
    :meth:`Participant.rehydrate`). Tests substitute an in-memory fake.

    **Who consumes it.** Every Participants command/query handler that reads or
    mutates a participant.

    Contract notes: the ``get_*`` lookups return ``None`` when nothing matches.
    ``save`` performs an upsert keyed by :attr:`Participant.id`, enforces the
    aggregate's optimistic-concurrency :attr:`Participant.version`, and persists the
    owned guardian relationships. Uniqueness of the display alias is a
    persistence-level invariant the adapter guards; ``exists_by_display_alias`` lets
    a use case check it up front without loading the aggregate.
    """

    def get(self, participant_id: ParticipantId) -> Participant | None:
        """Return the participant with ``participant_id``, or ``None`` if none exists."""
        ...

    def get_by_display_alias(self, alias: DisplayAlias) -> Participant | None:
        """Return the active participant whose display alias is ``alias``, or ``None``."""
        ...

    def exists(self, participant_id: ParticipantId) -> bool:
        """Whether a participant with ``participant_id`` is stored."""
        ...

    def exists_by_display_alias(self, alias: DisplayAlias) -> bool:
        """Whether some active participant currently uses ``alias`` (uniqueness pre-check)."""
        ...

    def save(self, participant: Participant) -> None:
        """Persist ``participant`` (insert or update), honouring its optimistic version."""
        ...

    def delete(self, participant: Participant) -> None:
        """Remove ``participant`` from storage.

        This is a *storage* deletion; the reversible business lifecycle transition
        is :meth:`Participant.archive`, and the privacy-driven terminal transition is
        :meth:`Participant.request_erasure`. A hard ``delete`` is reserved for
        legally mandated erasure of the record.
        """
        ...


# ---------------------------------------------------------------------------
# Ambient-dependency ports (time & identity, injected not read globally)
# ---------------------------------------------------------------------------


@runtime_checkable
class Clock(Protocol):
    """Port: the source of the current instant, injected rather than read globally.

    **Why it exists.** The domain already takes ``now`` as an argument to stay
    deterministic; this port is how the application layer *obtains* that ``now``
    without calling :func:`datetime.now` directly, so use cases are testable with a
    frozen clock.

    **Who implements it.** A trivial system-clock adapter in infrastructure. Tests
    inject a fixed fake clock.

    Contract note: both methods return **timezone-aware** datetimes. :meth:`utcnow`
    is the canonical UTC instant the platform stores (API-000 §22).
    """

    def now(self) -> datetime:
        """The current instant as a timezone-aware datetime (possibly non-UTC zone)."""
        ...

    def utcnow(self) -> datetime:
        """The current instant as a timezone-aware **UTC** datetime."""
        ...


@runtime_checkable
class UuidGenerator(Protocol):
    """Port: source of fresh UUID v7 identifiers, injected rather than read globally.

    **Why it exists.** Identifiers for new aggregates must be time-ordered UUID v7
    (API-000 §23) yet generated deterministically under test. Injecting this port
    lets a use case obtain an id without calling into ``uuid`` directly.

    **Who implements it.** An infrastructure adapter wrapping the platform's UUID v7
    generation. Tests inject a sequence-driven fake for reproducible ids.

    Contract note: the returned value must be a UUID **version 7**; downstream value
    objects (:class:`ParticipantId`) reject any other version.
    """

    def new(self) -> uuid.UUID:
        """Return a brand-new time-ordered UUID version 7."""
        ...


@runtime_checkable
class EventPublisher(Protocol):
    """Port: dispatch recorded domain events to the world outside the aggregate.

    **Why it exists.** Domain methods only *return* events; they never publish them
    (ARCH-001 §4.8). Some component must carry those facts to consumers — other
    bounded contexts, projections, side-effect handlers — and use cases must do so
    without binding to a concrete bus.

    **Who implements it.** An infrastructure adapter writing to the transactional
    outbox / message bus so publication commits atomically with the aggregate
    ``save``. Tests use a recording fake.

    Contract note: takes a :class:`~collections.abc.Sequence` so a handler can pass
    the event list a domain method returned as-is; an empty sequence is a valid
    no-op.
    """

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Publish ``events`` in order to the platform's event transport."""
        ...
