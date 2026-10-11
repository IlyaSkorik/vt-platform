"""Ports the Programs use cases depend on (ARCH-001 §7.3, Dependency Inversion).

Protocols only: the application layer states what it needs, and
:mod:`apps.programs.composition` decides which adapter satisfies it. Nothing here
imports Django, so the use cases are testable against plain in-memory fakes.

:class:`PerformanceCatalog` is the anti-corruption layer around the Applications and
Competitions contexts: it answers "which acts may this program contain, and what do
they look like" in *this* context's language. Programs never touches another
context's aggregates or tables directly.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from apps.programs.application.dto import ProgramTableView
from apps.programs.domain.entities import Program

__all__ = [
    "CatalogPerformance",
    "Clock",
    "PerformanceCatalog",
    "ProgramRepository",
    "SlugFactory",
    "TableRenderer",
]


@dataclass(frozen=True, slots=True)
class CatalogPerformance:
    """One competing act as the Programs context needs to see it.

    A flat, resolved projection - names already joined, taxonomy already looked up -
    so neither the use cases nor the presentation edge has to know how Applications
    stores a submission. ``comment`` is the applicant's note for the organizers about
    the act (stage entry, props, backing-track quirks), which is precisely the
    information a running order exists to carry.
    """

    submission_id: uuid.UUID
    title: str
    duration_seconds: int
    nomination_id: uuid.UUID | None = None
    nomination: str | None = None
    discipline: str | None = None
    age_category: str | None = None
    #: Where the act's age band sits among the competition's others. Carried beside the
    #: band's name because "7-9 лет" and "10-12 лет" do not sort as ages when sorted as
    #: text, and a generated programme is read youngest-first.
    age_order: int | None = None
    participant_group: str | None = None
    participation_format: str | None = None
    participants: tuple[str, ...] = ()
    #: How many people actually stand on stage. A collective states its own headcount on
    #: the entry form; a solo (or an entry that never stated one) counts the performers
    #: it listed. Carried as a number rather than ``len(participants)`` because those are
    #: two different facts: a collective is one participant row and twenty people.
    participant_count: int = 0
    teachers: tuple[str, ...] = ()
    #: Who to ring about this act, best contact first: the phones of its teachers as the
    #: directory holds them, and the applicant's own if no teacher has one. Plural
    #: because an act prepared by two teachers legitimately has two numbers.
    contacts: tuple[str, ...] = ()
    organization: str | None = None
    comment: str | None = None
    status: str = ""

    @property
    def lead_participant(self) -> str | None:
        """The name a program line is headed with."""
        return self.participants[0] if self.participants else None


class ProgramRepository(Protocol):
    """Persistence port for the :class:`Program` aggregate."""

    def get(self, program_id: uuid.UUID) -> Program | None:
        """Load one program with its items and public editions, or ``None``."""
        ...

    def list_for_competition(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID | None = None) -> tuple[Program, ...]:
        """Every live program of a competition, newest last."""
        ...

    def save(self, program: Program) -> None:
        """Persist the aggregate as one unit (root, items and shares together)."""
        ...

    def slug_taken(self, slug: str) -> bool:
        """Whether a live public edition already uses this slug."""
        ...

    def get_by_slug(self, slug: str) -> tuple[Program, uuid.UUID] | None:
        """Resolve a public link to its program and the id of the edition it names.

        The public edge needs no aggregate loaded by id and no organizer context - a
        slug is the whole of its input.
        """
        ...

    def stamp_for_slug(self, slug: str) -> tuple[uuid.UUID, int] | None:
        """The edition's id and its program's version, without loading the aggregate.

        Exists for the one caller that asks "has anything changed?" far more often than
        it asks "what is it?" - the public screen, polling every few seconds. Answering
        that from one indexed row beats loading items, editions, columns and the whole
        catalog read behind them, only to find nothing moved.
        """
        ...


class PerformanceCatalog(Protocol):
    """Anti-corruption layer over Applications + Competitions."""

    def competing_performances(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID | None = None,
    ) -> tuple[CatalogPerformance, ...]:
        """The acts of a competition that are actually taking part, in a stable order."""
        ...

    def performances_by_id(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CatalogPerformance]:
        """Resolve specific acts - used to render a program's existing slots."""
        ...

    def music_references(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, tuple[str, ...]]:
        """The stored backing-track references of each act, in upload order.

        Kept off :class:`CatalogPerformance` on purpose: every screen that renders a
        running order would then carry file keys it never shows. Only the archive
        download asks for these.
        """
        ...

    def media_references(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, tuple[str, ...]]:
        """The stored media references of each act — video and photographs, in upload order.

        A separate question from :meth:`music_references` because it answers a different
        need on the day: the screen operator wants what will be projected, and mixing it
        into the sound desk's archive would hand each of them the other's files.
        """
        ...

    def competition_title(self, competition_id: uuid.UUID) -> str | None:
        """The competition's title, for the heading of a public program."""
        ...

    def nomination_title(self, nomination_id: uuid.UUID) -> str | None:
        """The nomination's name, for the heading of a public program."""
        ...


class Clock(Protocol):
    """The current instant, injected so time is never read from the domain."""

    def utcnow(self) -> datetime:
        """The current UTC instant."""
        ...


class SlugFactory(Protocol):
    """Mints the unguessable token a public program is reached by."""

    def new_slug(self) -> str:
        """A fresh candidate slug."""
        ...


class TableRenderer(Protocol):
    """Turns a rendered table into a document the organizer can print or send.

    Deliberately ignorant of programmes: it is handed a heading, columns and rows of text
    and returns bytes. That keeps the layout rules (page size, wrapping, repeating the
    header on each page) in one adapter, and keeps every decision about *what* a cell says
    in the application layer, where the public screen decides it too.
    """

    def render(self, table: ProgramTableView) -> bytes:
        """Render the table; the caller knows the media type it asked for."""
        ...
