"""In-memory fakes for the Participants application ports.

Framework-free, database-free test doubles that structurally satisfy the ports in
:mod:`apps.participants.application.interfaces`. They record their interactions so
tests can assert on them. Domain **policies** are pure, deterministic value objects
and are used for real (not faked) by the tests.

This module is not a test module (no ``test_`` prefix), so pytest does not collect
it; it is imported by the handler tests.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.participants.domain.entities import Participant
from apps.participants.domain.events import DomainEvent
from apps.participants.domain.value_objects import DisplayAlias, ParticipantId

#: Fixed reference instant shared by the fake clock and the tests.
NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


class FakeParticipantRepository:
    """In-memory :class:`ParticipantRepository` keyed by :class:`ParticipantId`."""

    def __init__(self) -> None:
        self._by_id: dict[ParticipantId, Participant] = {}
        self.saved: list[Participant] = []
        self.deleted: list[Participant] = []

    def get(self, participant_id: ParticipantId) -> Participant | None:
        return self._by_id.get(participant_id)

    def get_by_display_alias(self, alias: DisplayAlias) -> Participant | None:
        return next(
            (p for p in self._by_id.values() if p.display_alias == alias and not p.is_erased()),
            None,
        )

    def exists(self, participant_id: ParticipantId) -> bool:
        return participant_id in self._by_id

    def exists_by_display_alias(self, alias: DisplayAlias) -> bool:
        return any(
            p.display_alias == alias and not p.is_erased() for p in self._by_id.values()
        )

    def save(self, participant: Participant) -> None:
        self._by_id[participant.id] = participant
        self.saved.append(participant)

    def delete(self, participant: Participant) -> None:
        self._by_id.pop(participant.id, None)
        self.deleted.append(participant)

    # Test convenience: seed a participant without going through ``save`` bookkeeping.
    def seed(self, participant: Participant) -> Participant:
        self._by_id[participant.id] = participant
        return participant


class FakeClock:
    """:class:`Clock` fake frozen at a fixed instant."""

    def __init__(self, moment: datetime = NOW) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment

    def utcnow(self) -> datetime:
        return self._moment.astimezone(UTC)


class FakeUuidGenerator:
    """:class:`UuidGenerator` fake producing fresh UUID v7 values, recording them."""

    def __init__(self) -> None:
        self.issued: list[uuid.UUID] = []

    def new(self) -> uuid.UUID:
        value = ParticipantId.generate().value
        self.issued.append(value)
        return value


class FakeEventPublisher:
    """:class:`EventPublisher` fake recording every published batch."""

    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)
