"""Application ports (contracts) required by Applications (Competition Submission) use cases.

The **outbound dependencies** of the Applications application layer, expressed as
pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion). A use
case depends only on these abstractions; concrete adapters (a Django ORM
repository, a Competition read-model gateway, a clock, a UUID source, an event
publisher) live in ``infrastructure/`` and are injected at composition time. The
dependency arrow points *inward*: infrastructure depends on this module, never the
reverse.

**Framework-free** (ARCH-001 §4.1, §7.2): standard library and this context's
domain only. Interfaces only, no implementations - this iteration declares the
ports; the use cases that consume them are a later iteration.

The :class:`Submission` is the sole aggregate root of this context, so there is a
single repository. It persists and retrieves the **whole aggregate** - the root
plus its child entities (participants, teachers, attachments, reviews) and its
value objects (the performance and the price snapshot) - as one unit, because they
share one consistency boundary.

:class:`CompetitionCatalog` is the **anti-corruption gateway** to the Competition
context: it returns a :class:`SubmissionParticipationPolicy` read model (a local
projection), so the Submission validates admissibility and participant-count rules
without ever importing the Competition aggregate.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.applications.domain.entities import Submission
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    CompetitionId,
    DisciplineId,
    NominationId,
    ParticipantGroupId,
    ParticipationFormatId,
    SubmissionId,
    SubmissionParticipationPolicy,
    UserId,
)

__all__ = [
    "Clock",
    "CompetitionCatalog",
    "EventPublisher",
    "SubmissionRepository",
    "UuidGenerator",
]


# ---------------------------------------------------------------------------
# Repository port
# ---------------------------------------------------------------------------


@runtime_checkable
class SubmissionRepository(Protocol):
    """Port: persistence & retrieval of the :class:`Submission` aggregate.

    Loads and saves the entire aggregate graph atomically, honouring the root's
    optimistic-concurrency ``version``. Getters report absence as ``None`` rather
    than raising, leaving the "not found" decision to the use case.
    """

    def get(self, submission_id: SubmissionId) -> Submission | None:
        """Return the submission with ``submission_id`` (whole aggregate), or ``None``."""
        ...

    def exists(self, submission_id: SubmissionId) -> bool:
        """Whether a submission with ``submission_id`` exists (no aggregate materialized)."""
        ...

    def list_by_applicant(self, applicant_id: UserId) -> Sequence[Submission]:
        """Return all non-deleted submissions owned by ``applicant_id``."""
        ...

    def list_by_competition(self, competition_id: CompetitionId) -> Sequence[Submission]:
        """Return all non-deleted submissions for ``competition_id``."""
        ...

    def save(self, submission: Submission) -> None:
        """Persist ``submission`` and its whole graph (insert or update), honouring its version."""
        ...


# ---------------------------------------------------------------------------
# Competition anti-corruption gateway (read model)
# ---------------------------------------------------------------------------


@runtime_checkable
class CompetitionCatalog(Protocol):
    """Port: the anti-corruption gateway to the Competition context.

    Translates the foreign Competition configuration into this context's own
    read-model value object. The application layer calls this before
    :meth:`Submission.submit` and passes the result in, so the domain validates
    admissibility and participant-count rules against a local projection - never by
    importing the Competition aggregate.

    Returns ``None`` when the referenced competition or combination is unknown,
    leaving the "not found" decision to the use case.
    """

    def participation_policy(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: NominationId,
        discipline_id: DisciplineId,
        age_category_id: AgeCategoryId,
        participant_group_id: ParticipantGroupId,
        participation_format_id: ParticipationFormatId,
    ) -> SubmissionParticipationPolicy | None:
        """Return the participation policy for a combination, or ``None`` if unknown."""
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
