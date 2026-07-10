"""Application ports (contracts) required by Competitions use cases.

The **outbound dependencies** of the Competitions application layer, expressed as
pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion). A use
case depends only on these abstractions; concrete adapters (a Django ORM
repository, a clock, a UUID source, an event publisher) live in
``infrastructure/`` and are injected at composition time. The dependency arrow
points *inward*: infrastructure depends on this module, never the reverse.

**Framework-free** (ARCH-001 §4.1, §7.2): standard library only. Interfaces only,
no implementations. The repository getter returns ``... | None`` so the *use case*
decides whether absence is an error.

The :class:`Competition` is the sole aggregate root of this context, so there is a
single repository. It persists and retrieves the **whole aggregate** — the root
plus its child entities (categories, disciplines, age categories, participant
groups, regulations, documents) and its configuration value objects (admission
and pricing rules) — as one unit, because they share one consistency boundary.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.competitions.domain.entities import Competition
from apps.competitions.domain.events import DomainEvent
from apps.competitions.domain.templates import CompetitionTemplate
from apps.competitions.domain.value_objects import CompetitionId, Season, TemplateId

__all__ = [
    "Clock",
    "CompetitionRepository",
    "CompetitionTemplateRepository",
    "EventPublisher",
    "UuidGenerator",
]


# ---------------------------------------------------------------------------
# Repository port
# ---------------------------------------------------------------------------


@runtime_checkable
class CompetitionRepository(Protocol):
    """Port: persistence & retrieval of the :class:`Competition` aggregate.

    Loads and saves the entire aggregate graph atomically, honouring the root's
    optimistic-concurrency ``version``. Getters report absence as ``None`` rather
    than raising, leaving the "not found" decision to the use case.
    """

    def get(self, competition_id: CompetitionId) -> Competition | None:
        """Return the competition with ``competition_id`` (whole aggregate), or ``None``."""
        ...

    def exists(self, competition_id: CompetitionId) -> bool:
        """Whether a competition with ``competition_id`` exists (no aggregate materialized)."""
        ...

    def list_by_season(self, season: Season) -> Sequence[Competition]:
        """Return all non-deleted competitions in ``season``."""
        ...

    def list_all(self) -> Sequence[Competition]:
        """Return all non-deleted competitions."""
        ...

    def save(self, competition: Competition) -> None:
        """Persist ``competition`` and its whole graph (insert or update), honouring its version."""
        ...


@runtime_checkable
class CompetitionTemplateRepository(Protocol):
    """Port: persistence & retrieval of the :class:`CompetitionTemplate` aggregate.

    A template is a distinct aggregate (its own consistency boundary), so it has its
    own repository. ``Competition.from_template`` reads a loaded template; this port
    is how a use case fetches one to stamp out a new competition.
    """

    def get(self, template_id: TemplateId) -> CompetitionTemplate | None:
        """Return the template with ``template_id`` (whole aggregate), or ``None``."""
        ...

    def list_all(self) -> Sequence[CompetitionTemplate]:
        """Return all non-deleted templates."""
        ...

    def save(self, template: CompetitionTemplate) -> None:
        """Persist ``template`` and its whole graph (insert or update), honouring its version."""
        ...


# ---------------------------------------------------------------------------
# Ambient-dependency ports (time & identity, injected not read globally)
# ---------------------------------------------------------------------------


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
