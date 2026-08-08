"""Ports the Results use cases depend on (ARCH-001 §7.3, Dependency Inversion).

Protocols only: the application layer states what it needs and
:mod:`apps.results.composition` decides which adapter satisfies it. Nothing here
imports Django, so the use cases are testable against plain in-memory fakes.

Four of these are anti-corruption layers, and it is worth being explicit about the
direction each one points, because publishing results is the one operation in this
platform that writes into another context:

* :class:`PerformanceCatalog` **reads** Applications + Competitions - which acts
  competed in this nomination, and what their names are today.
* :class:`RunningOrderSource` **reads** Programs - the order and the numbers a protocol
  is seeded from, so the jury's table arrives in the order the day actually ran.
* :class:`AwardRegister` **writes** Diplomas - the one place a degree ever lands on a
  diploma. A port rather than a direct call because "publish the results" must not
  depend on how a diploma is stored, numbered or rendered.
* :class:`ResultsNotifier` **writes** to the outside world - one letter per applicant
  once the results are out.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol as TypingProtocol

from apps.results.domain.entities import Protocol

__all__ = [
    "AwardRegister",
    "AwardedDiploma",
    "CatalogPerformance",
    "Clock",
    "PerformanceCatalog",
    "ProtocolRepository",
    "ResultsNotifier",
    "RunningOrderEntry",
    "RunningOrderSource",
    "SlugFactory",
]


@dataclass(frozen=True, slots=True)
class CatalogPerformance:
    """One competing act as the Results context needs to see it.

    A flat, resolved projection - names already joined, taxonomy already looked up - so
    neither the use cases nor the presentation edge has to know how Applications stores
    a submission. ``applicant_id`` and ``applicant_email`` are what a results letter is
    addressed with: the account that entered the act, not the child who performed it.
    """

    submission_id: uuid.UUID
    title: str
    applicant_id: uuid.UUID | None = None
    applicant_email: str | None = None
    applicant_name: str | None = None
    nomination_id: uuid.UUID | None = None
    nomination: str | None = None
    discipline: str | None = None
    age_category: str | None = None
    participant_group: str | None = None
    participation_format: str | None = None
    participants: tuple[str, ...] = ()
    teachers: tuple[str, ...] = ()
    organization: str | None = None

    @property
    def lead_participant(self) -> str | None:
        """The name a protocol line is headed with."""
        return self.participants[0] if self.participants else None


@dataclass(frozen=True, slots=True)
class RunningOrderEntry:
    """One performance slot of a programme: the act, and the number it went on under.

    Deliberately not the programme's whole item - a protocol has no use for durations,
    breaks or clock times. Blocks (a break, an award ceremony) never reach this shape at
    all, because nothing awards a result to a lunch break.
    """

    submission_id: uuid.UUID
    number: int


@dataclass(frozen=True, slots=True)
class AwardedDiploma:
    """What the diploma register did with one awarded row.

    ``number`` is the diploma's own permanent number and ``created`` says whether this
    publication is what brought it into existence - the two facts an organizer needs to
    reconcile a published protocol against the diploma register.
    """

    submission_id: uuid.UUID
    number: str
    degree: str
    created: bool
    #: The participant-facing document, once one exists. ``None`` when the nomination
    #: has no diploma template yet: the degree is recorded and the PDF follows later,
    #: rather than the whole publication failing over a missing template.
    file_url: str | None = None


class ProtocolRepository(TypingProtocol):
    """Persistence port for the :class:`Protocol` aggregate."""

    def get(self, protocol_id: uuid.UUID) -> Protocol | None:
        """Load one protocol with its rows, or ``None``."""
        ...

    def list_for_competition(self, competition_id: uuid.UUID) -> tuple[Protocol, ...]:
        """Every live protocol of a competition, oldest first."""
        ...

    def get_for_nomination(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> Protocol | None:
        """The nomination's protocol, or ``None`` - the one-per-nomination check."""
        ...

    def list_published_for_competition(self, competition_id: uuid.UUID) -> tuple[Protocol, ...]:
        """Every published protocol of a competition - what the landing page lists."""
        ...

    def save(self, protocol: Protocol) -> None:
        """Persist the aggregate as one unit (root row and its rows together)."""
        ...

    def slug_taken(self, slug: str) -> bool:
        """Whether any protocol - live, unpublished or deleted - has used this slug."""
        ...

    def get_by_slug(self, slug: str) -> Protocol | None:
        """Resolve a public link to its protocol, or ``None``.

        Answers ``None`` for a protocol that is not currently published: unpublishing
        must take the page down, and a slug is the whole of the public edge's input.
        """
        ...


class PerformanceCatalog(TypingProtocol):
    """Anti-corruption layer over Applications + Competitions."""

    def competing_performances(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
    ) -> tuple[CatalogPerformance, ...]:
        """The acts of one nomination that actually competed, in a stable order."""
        ...

    def performances_by_id(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CatalogPerformance]:
        """Resolve specific acts - used to render a protocol's existing rows."""
        ...

    def competition_title(self, competition_id: uuid.UUID) -> str | None:
        """The competition's title, for the heading of a public protocol."""
        ...

    def nomination_title(self, nomination_id: uuid.UUID) -> str | None:
        """The nomination's name, for the heading of a public protocol."""
        ...


class RunningOrderSource(TypingProtocol):
    """Anti-corruption layer over the Programs context.

    Read-only and one-directional: a protocol is *seeded* from a running order and then
    owns its own copy. Programs never learns that Results exists, and a programme
    rearranged after the ceremony cannot move a result.
    """

    def running_order(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> tuple[RunningOrderEntry, ...]:
        """The performance slots of this nomination's programmes, in running order.

        Empty when the nomination has no programme - a competition run without one is
        perfectly normal, and the caller then falls back to the catalog.
        """
        ...

    def program_id_for(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> uuid.UUID | None:
        """Which programme the order above came from, for the record."""
        ...


class AwardRegister(TypingProtocol):
    """Anti-corruption layer over the Diplomas context - the write side of publishing.

    One method, called once per publication, and the **only** path by which a degree
    reaches a diploma anywhere in the platform. Everything about how that happens -
    finding or creating the diploma, writing ``award.degree``, rendering the
    participant's copy, marking it issued - is the adapter's business.

    Idempotent by contract: publishing revision 3 of a protocol must correct the degrees
    written by revision 2 rather than issue a second set of diplomas.
    """

    def record_awards(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
        awards: Sequence[tuple[uuid.UUID, str]],
        now: datetime,
    ) -> tuple[AwardedDiploma, ...]:
        """Write ``(submission id, degree label)`` pairs onto their diplomas.

        Returns one entry per diploma that now carries a degree. A submission whose
        diploma cannot be resolved at all is skipped rather than failing the batch: the
        protocol is still the record of what the jury decided, and an organizer can see
        the gap in the response.
        """
        ...


class ResultsNotifier(TypingProtocol):
    """Tells the people the results are about that the results exist."""

    def notify_results_published(
        self,
        *,
        user_id: str,
        email: str,
        applicant_name: str | None,
        competition_title: str | None,
        nomination_title: str | None,
        results: Sequence[tuple[str, str]],
        protocol_url: str,
    ) -> None:
        """One letter to one applicant: their results, and where to read the protocol.

        ``results`` is ``(what performed, what it won)`` for every act of theirs in this
        protocol, so an applicant who entered four numbers gets one letter rather than
        four - the difference between a notification and a mail flood when a studio has
        entered thirty acts.
        """
        ...


class Clock(TypingProtocol):
    """The current instant, injected so time is never read from the domain."""

    def utcnow(self) -> datetime:
        """The current UTC instant."""
        ...


class SlugFactory(TypingProtocol):
    """Mints the token a published protocol is reached by."""

    def new_slug(self) -> str:
        """A fresh candidate slug (the caller checks it is free)."""
        ...
