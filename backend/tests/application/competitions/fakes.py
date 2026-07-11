"""In-memory fakes for the Competitions application ports.

Structurally satisfy the ``application/interfaces`` protocols so command/query
handlers can be exercised without Django or a database (ARCH-001 §28). The fake
repository stores whole aggregates by id; the clock is frozen; the uuid source
yields real UUID v7 values (the domain id VOs reject anything else); the
publisher records what it was handed.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.competitions.domain.entities import Competition
from apps.competitions.domain.events import DomainEvent
from apps.competitions.domain.value_objects import CompetitionId, Season
from apps.competitions.infrastructure.system import Uuid7Generator


def new_uuid7() -> uuid.UUID:
    """A fresh UUID v7 (via the real adapter, so it is typed and valid)."""
    return Uuid7Generator().new()


class FakeClock:
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def utcnow(self) -> datetime:
        return self._now


class FakeUuidGenerator:
    def new(self) -> uuid.UUID:
        return new_uuid7()


class RecordingPublisher:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)


class InMemoryCompetitionRepository:
    def __init__(self) -> None:
        self._store: dict[str, Competition] = {}

    def get(self, competition_id: CompetitionId) -> Competition | None:
        return self._store.get(competition_id.json())

    def exists(self, competition_id: CompetitionId) -> bool:
        return competition_id.json() in self._store

    def list_by_season(self, season: Season) -> list[Competition]:
        return [c for c in self._store.values() if c.season == season]

    def list_all(self) -> list[Competition]:
        return list(self._store.values())

    def save(self, competition: Competition) -> None:
        self._store[competition.id.json()] = competition
