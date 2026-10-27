"""In-memory doubles for the Programs ports.

The use cases are written against protocols, so they can be exercised without
PostgreSQL, without other bounded contexts and without a real clock - which is what
makes assertions about *behaviour* (a fill that skips what is already scheduled, a
slug retried on collision) cheap and exact.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.programs.application.interfaces import CatalogApplicant, CatalogPerformance
from apps.programs.domain.entities import Program, ProgramItem

__all__ = [
    "FixedClock",
    "InMemoryProgramRepository",
    "RecordingPerformanceSchedule",
    "ScriptedSlugFactory",
    "StubPerformanceCatalog",
]


class FixedClock:
    """A clock that never moves, so every timestamp in a test is predictable."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 8, 1, 9, 0, tzinfo=UTC)

    def utcnow(self) -> datetime:
        return self._now


class ScriptedSlugFactory:
    """Hands out slugs from a script, so collisions can be arranged."""

    def __init__(self, *slugs: str) -> None:
        self._slugs = list(slugs) or ["Slug0001xy"]
        self.calls = 0

    def new_slug(self) -> str:
        self.calls += 1
        return self._slugs[min(self.calls - 1, len(self._slugs) - 1)]


class InMemoryProgramRepository:
    """Stores aggregates by reference - no serialization, no soft-delete filtering."""

    def __init__(self) -> None:
        self.programs: dict[uuid.UUID, Program] = {}
        self.claimed_slugs: set[str] = set()
        # What the real adapter's soft-delete leaves behind: the items a save dropped,
        # keyed by the instant it dropped them at. Undoing a rebuild reads this back.
        self.retired: dict[uuid.UUID, dict[datetime, tuple[ProgramItem, ...]]] = {}
        self._last_saved_items: dict[uuid.UUID, tuple[ProgramItem, ...]] = {}

    def get(self, program_id: uuid.UUID) -> Program | None:
        program = self.programs.get(program_id)
        if program is None or program.deleted_at is not None:
            return None
        return program

    def list_for_competition(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID | None = None) -> tuple[Program, ...]:
        return tuple(
            program
            for program in self.programs.values()
            if program.deleted_at is None
            and program.competition_id == competition_id
            and (nomination_id is None or program.nomination_id == nomination_id)
        )

    def save(self, program: Program) -> None:
        kept = {item.id for item in program.items}
        dropped = tuple(item for item in self._last_saved_items.get(program.id, ()) if item.id not in kept)
        if dropped:
            self.retired.setdefault(program.id, {})[program.updated_at] = dropped
        self._last_saved_items[program.id] = program.items
        self.programs[program.id] = program
        for share in program.shares:
            self.claimed_slugs.add(str(share.slug))

    def items_retired_at(self, program_id: uuid.UUID, moment: datetime) -> tuple[ProgramItem, ...]:
        return self.retired.get(program_id, {}).get(moment, ())

    def submission_ids_with_slots(self, submission_ids: Sequence[uuid.UUID]) -> frozenset[uuid.UUID]:
        wanted = set(submission_ids)
        seated: set[uuid.UUID] = set()
        for program in self.programs.values():
            if program.deleted_at is not None:
                continue
            seated.update(wanted.intersection(program.performance_submission_ids))
        return frozenset(seated)

    def slug_taken(self, slug: str) -> bool:
        return slug in self.claimed_slugs

    def get_by_slug(self, slug: str) -> tuple[Program, uuid.UUID] | None:
        for program in self.programs.values():
            if program.deleted_at is not None:
                continue
            for share in program.shares:
                if str(share.slug) == slug:
                    return program, share.id
        return None

    def stamp_for_slug(self, slug: str) -> tuple[uuid.UUID, int] | None:
        found = self.get_by_slug(slug)
        if found is None:
            return None
        program, share_id = found
        return share_id, program.version


class StubPerformanceCatalog:
    """A fixed catalog of competing acts, standing in for other contexts."""

    def __init__(
        self,
        *performances: CatalogPerformance,
        competition: str = "Весенний фестиваль",
        nomination: str = "Вокал",
        music: dict[uuid.UUID, tuple[str, ...]] | None = None,
        media: dict[uuid.UUID, tuple[str, ...]] | None = None,
        applicants: dict[uuid.UUID, CatalogApplicant] | None = None,
    ) -> None:
        self.performances = list(performances)
        self._competition = competition
        self._nomination = nomination
        self._music = music or {}
        self._media = media or {}
        self._applicants = applicants or {}

    def competing_performances(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID | None = None,
    ) -> tuple[CatalogPerformance, ...]:
        if nomination_id is None:
            return tuple(self.performances)
        return tuple(p for p in self.performances if p.nomination_id == nomination_id)

    def performances_by_id(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CatalogPerformance]:
        wanted = set(submission_ids)
        return {p.submission_id: p for p in self.performances if p.submission_id in wanted}

    def music_references(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, tuple[str, ...]]:
        wanted = set(submission_ids)
        return {key: value for key, value in self._music.items() if key in wanted}

    def media_references(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, tuple[str, ...]]:
        return {sid: self._media[sid] for sid in submission_ids if sid in self._media}

    def applicants_for(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CatalogApplicant]:
        return {sid: self._applicants[sid] for sid in submission_ids if sid in self._applicants}

    def competition_title(self, competition_id: uuid.UUID) -> str | None:
        return self._competition

    def nomination_title(self, nomination_id: uuid.UUID) -> str | None:
        return self._nomination


class RecordingPerformanceSchedule:
    """Records what the running order told the Applications context, in order.

    Two logs rather than one with a flag: every assertion about this port is about
    *which* way an act moved, and a test that has to unpack a tuple to find out
    reads worse than one that names the list it looks in.
    """

    def __init__(self) -> None:
        self.scheduled: list[uuid.UUID] = []
        self.unscheduled: list[uuid.UUID] = []

    def mark_scheduled(self, submission_ids: Sequence[uuid.UUID]) -> None:
        self.scheduled.extend(submission_ids)

    def mark_unscheduled(self, submission_ids: Sequence[uuid.UUID]) -> None:
        self.unscheduled.extend(submission_ids)
