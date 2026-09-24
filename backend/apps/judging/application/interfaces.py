"""Ports the Judging use cases depend on (ARCH-001 §7.3, Dependency Inversion).

Protocols only: the application layer states what it needs and
:mod:`apps.judging.composition` decides which adapter satisfies it. Nothing here
imports Django, so the use cases are testable against plain in-memory fakes.

Four of these are anti-corruption layers, and the direction each points is worth
stating because this context both reads a lot and writes into two others:

* :class:`CompetitionDirectory` **reads** Competitions — the genres and nominations an
  organizer writes criteria against, and whether this festival judges online at all.
* :class:`PerformanceDirectory` **reads** Applications + Programs — which acts are
  competing, where each sits in the taxonomy, its number, and what a judge may be
  shown about it. Deliberately *not* the participants' names: a judge is shown the act
  (ADR-0013), and a port that returned names would be one careless serializer away
  from putting them on a tablet.
* :class:`ProtocolWriter` **writes** Results — the computed awards, landing in the
  protocol the organizer publishes.
* :class:`JuryNotifier` **writes** to the outside world — the invitation a judge gets.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol as TypingProtocol

from apps.judging.domain.entities import JudgingSetup, JuryMember, PerformanceScoring, Scorecard

__all__ = [
    "AppliedAward",
    "Clock",
    "CompetitionDirectory",
    "DirectoryNomination",
    "DirectoryPerformance",
    "JudgingSetupRepository",
    "JuryMemberRepository",
    "JuryNotifier",
    "PerformanceDirectory",
    "PerformanceScoringRepository",
    "ProtocolWriter",
    "ScorecardRepository",
    "SlugFactory",
    "TokenFactory",
    "UuidGenerator",
]


# ---------------------------------------------------------------------------
# Projections crossing the boundary
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DirectoryNomination:
    """One genre and the nominations under it, as the criteria screen needs them."""

    category_id: uuid.UUID
    name: str
    sort_order: int
    disciplines: tuple[tuple[uuid.UUID, str], ...] = ()


@dataclass(frozen=True, slots=True)
class DirectoryPerformance:
    """One competing act as Judging needs to see it.

    :attr:`title` is the name of the act and :attr:`number` the slot it performed
    under. There is no participant here on purpose — see the module docstring.

    :attr:`organization` is the one piece of provenance a judge is given, because a
    panel is routinely asked to note which studio an act came from and because it
    names an institution rather than a child.
    """

    submission_id: uuid.UUID
    title: str
    category_id: uuid.UUID
    discipline_id: uuid.UUID | None = None
    age_category_id: uuid.UUID | None = None
    participation_format_id: uuid.UUID | None = None
    number: int = 0
    category_name: str | None = None
    discipline_name: str | None = None
    age_category_name: str | None = None
    participation_format_name: str | None = None
    organization: str | None = None


# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------


class Clock(TypingProtocol):
    """The current instant, injected so use cases are testable without waiting."""

    def utcnow(self) -> datetime: ...


class UuidGenerator(TypingProtocol):
    """Fresh, time-ordered identifiers (API-000 §23)."""

    def new(self) -> uuid.UUID: ...


class SlugFactory(TypingProtocol):
    """Mints the public slug the hall's board is reached by."""

    def new_slug(self) -> str: ...


class TokenFactory(TypingProtocol):
    """Mints the single-use secret an invitation link carries."""

    def new_token(self) -> str: ...


class JudgingSetupRepository(TypingProtocol):
    """Persistence for the one configuration row a competition has."""

    def get(self, competition_id: uuid.UUID) -> JudgingSetup | None: ...

    def by_board_slug(self, slug: str) -> JudgingSetup | None: ...

    def save(self, setup: JudgingSetup) -> None: ...


class JuryMemberRepository(TypingProtocol):
    """Persistence for the panel."""

    def get(self, member_id: uuid.UUID) -> JuryMember | None: ...

    def by_competition(self, competition_id: uuid.UUID) -> tuple[JuryMember, ...]: ...

    def by_user(self, *, competition_id: uuid.UUID, user_id: uuid.UUID) -> JuryMember | None: ...

    def by_invitation_token(self, token: str) -> JuryMember | None: ...

    def competitions_for_user(self, user_id: uuid.UUID) -> tuple[JuryMember, ...]: ...

    def save(self, member: JuryMember) -> None: ...

    def delete(self, member_id: uuid.UUID) -> None: ...


class PerformanceScoringRepository(TypingProtocol):
    """Persistence for each act's open/closed state."""

    def get(self, *, competition_id: uuid.UUID, submission_id: uuid.UUID) -> PerformanceScoring | None: ...

    def by_competition(self, competition_id: uuid.UUID) -> tuple[PerformanceScoring, ...]: ...

    def current(self, competition_id: uuid.UUID) -> PerformanceScoring | None:
        """The act the host has open, if any — what a tablet and the board follow."""
        ...

    def save(self, scoring: PerformanceScoring) -> None: ...


class ScorecardRepository(TypingProtocol):
    """Persistence for the panel's sheets."""

    def get(self, *, competition_id: uuid.UUID, submission_id: uuid.UUID, jury_member_id: uuid.UUID) -> Scorecard | None: ...

    def by_submission(self, *, competition_id: uuid.UUID, submission_id: uuid.UUID) -> tuple[Scorecard, ...]: ...

    def by_submissions(self, *, competition_id: uuid.UUID, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, tuple[Scorecard, ...]]: ...

    def by_member(self, *, competition_id: uuid.UUID, jury_member_id: uuid.UUID) -> tuple[Scorecard, ...]: ...

    def save(self, scorecard: Scorecard) -> None: ...


class CompetitionDirectory(TypingProtocol):
    """Reads the Competitions context: taxonomy, title, and the judging mode."""

    def nominations(self, competition_id: uuid.UUID) -> tuple[DirectoryNomination, ...]: ...

    def competition_title(self, competition_id: uuid.UUID) -> str: ...

    def online_judging_enabled(self, competition_id: uuid.UUID) -> bool: ...

    def organizer_id(self, competition_id: uuid.UUID) -> uuid.UUID | None: ...


class PerformanceDirectory(TypingProtocol):
    """Reads Applications + Programs: who is competing, and in what order."""

    def performances(self, competition_id: uuid.UUID) -> tuple[DirectoryPerformance, ...]: ...

    def performances_by_id(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, DirectoryPerformance]: ...


class ProtocolWriter(TypingProtocol):
    """Writes Results: the computed awards, into the protocol the organizer publishes.

    One method, taking whole nominations at a time, because that is the unit a protocol
    is: pushing awards one act at a time would make a half-applied tally a state the
    organizer could see.
    """

    def apply_awards(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
        awards: Sequence[tuple[uuid.UUID, str | None]],
        now: datetime,
    ) -> int:
        """Write ``(submission id, award code)`` onto the nomination's protocol.

        Returns how many rows were changed. A submission with no row in the protocol is
        skipped rather than added: the protocol's contents are the organizer's call.
        """
        ...


class JuryNotifier(TypingProtocol):
    """Writes to the outside world: the invitation a judge receives."""

    def notify_jury_invited(
        self,
        *,
        email: str,
        full_name: str,
        competition_title: str,
        invitation_url: str,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class AppliedAward:
    """What one act ended up with, as reported back after a tally was applied."""

    submission_id: uuid.UUID
    score: Decimal | None
    award_code: str | None
    award_label: str | None
