"""In-memory doubles for the Results ports.

The use cases are written against protocols, so they can be exercised without PostgreSQL,
without the Diplomas context and without a real clock - which is what makes assertions
about *behaviour* (a seed that follows the running order, one letter per applicant, a
correction that reissues rather than duplicates) cheap and exact.

:class:`RecordingAwardRegister` and :class:`RecordingNotifier` are the two that matter:
publication's whole job is to have the right effect on them, and recording the calls is how
a test says so without a diploma renderer or an SMTP server anywhere in sight.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.results.application.interfaces import AwardedDiploma, CatalogPerformance, RunningOrderEntry
from apps.results.domain.entities import Protocol
from apps.results.domain.value_objects import ProtocolStatus

__all__ = [
    "FixedClock",
    "InMemoryProtocolRepository",
    "RecordingAwardRegister",
    "RecordingNotifier",
    "ScriptedSlugFactory",
    "StubPerformanceCatalog",
    "StubRunningOrderSource",
]


class FixedClock:
    """A clock that never moves, so every timestamp in a test is predictable."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 8, 1, 18, 0, tzinfo=UTC)

    def utcnow(self) -> datetime:
        return self._now


class ScriptedSlugFactory:
    """Hands out slugs from a script, so collisions can be arranged."""

    def __init__(self, *slugs: str) -> None:
        self._slugs = list(slugs) or ["Slugxy2345"]
        self.calls = 0

    def new_slug(self) -> str:
        self.calls += 1
        return self._slugs[min(self.calls - 1, len(self._slugs) - 1)]


class InMemoryProtocolRepository:
    """Stores aggregates by reference - no serialization, no soft-delete filtering."""

    def __init__(self) -> None:
        self.protocols: dict[uuid.UUID, Protocol] = {}
        self.claimed_slugs: set[str] = set()
        self.saves = 0

    def get(self, protocol_id: uuid.UUID) -> Protocol | None:
        protocol = self.protocols.get(protocol_id)
        if protocol is None or protocol.deleted_at is not None:
            return None
        return protocol

    def list_for_competition(self, competition_id: uuid.UUID) -> tuple[Protocol, ...]:
        return tuple(protocol for protocol in self.protocols.values() if protocol.deleted_at is None and protocol.competition_id == competition_id)

    def get_for_nomination(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> Protocol | None:
        for protocol in self.list_for_competition(competition_id):
            if protocol.nomination_id == nomination_id:
                return protocol
        return None

    def list_published_for_competition(self, competition_id: uuid.UUID) -> tuple[Protocol, ...]:
        return tuple(protocol for protocol in self.list_for_competition(competition_id) if protocol.is_published)

    def save(self, protocol: Protocol) -> None:
        self.saves += 1
        self.protocols[protocol.id] = protocol
        if protocol.slug is not None:
            # Claimed on save and never released, mirroring the unconditional unique
            # constraint: a slug that has existed must never be handed out again.
            self.claimed_slugs.add(str(protocol.slug))

    def slug_taken(self, slug: str) -> bool:
        return slug in self.claimed_slugs

    def get_by_slug(self, slug: str) -> Protocol | None:
        for protocol in self.protocols.values():
            if protocol.deleted_at is None and protocol.status is ProtocolStatus.PUBLISHED and str(protocol.slug) == slug:
                return protocol
        return None


class StubPerformanceCatalog:
    """A fixed catalog of competing acts, standing in for the other contexts."""

    def __init__(
        self,
        *performances: CatalogPerformance,
        competition: str = "Взлёт талантов 2026",
        nomination: str = "Вокал",
    ) -> None:
        self.performances = list(performances)
        self._competition = competition
        self._nomination = nomination

    def competing_performances(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> tuple[CatalogPerformance, ...]:
        return tuple(p for p in self.performances if p.nomination_id == nomination_id)

    def performances_by_id(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CatalogPerformance]:
        wanted = set(submission_ids)
        return {p.submission_id: p for p in self.performances if p.submission_id in wanted}

    def competition_title(self, competition_id: uuid.UUID) -> str | None:
        return self._competition

    def nomination_title(self, nomination_id: uuid.UUID) -> str | None:
        return self._nomination

    def forget(self, submission_id: uuid.UUID) -> None:
        """Drop an act, standing in for an entry deleted in Applications."""
        self.performances = [p for p in self.performances if p.submission_id != submission_id]


class StubRunningOrderSource:
    """A fixed running order, standing in for the Programs context.

    Constructed empty for the nomination judged without a printed programme, which is the
    fallback path the seed has to handle.
    """

    def __init__(self, *entries: RunningOrderEntry, program_id: uuid.UUID | None = None) -> None:
        self.entries = list(entries)
        self.program_id = program_id if program_id is not None or not entries else uuid.uuid4()

    def running_order(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> tuple[RunningOrderEntry, ...]:
        return tuple(self.entries)

    def program_id_for(self, *, competition_id: uuid.UUID, nomination_id: uuid.UUID) -> uuid.UUID | None:
        return self.program_id


class RecordingAwardRegister:
    """Records what publication asked the Diplomas context to do.

    ``missing`` is the submissions it refuses to resolve, standing in for a nomination with
    no diploma template - the partial outcome publication has to survive.
    """

    def __init__(self, *, missing: set[uuid.UUID] | None = None) -> None:
        self.calls: list[tuple[uuid.UUID, tuple[tuple[uuid.UUID, str], ...]]] = []
        self.issued: dict[uuid.UUID, str] = {}
        self._missing = missing or set()

    def record_awards(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
        awards: Sequence[tuple[uuid.UUID, str]],
        now: datetime,
    ) -> tuple[AwardedDiploma, ...]:
        self.calls.append((nomination_id, tuple(awards)))
        recorded: list[AwardedDiploma] = []
        for submission_id, degree in awards:
            if submission_id in self._missing:
                continue
            created = submission_id not in self.issued
            self.issued[submission_id] = degree
            recorded.append(
                AwardedDiploma(
                    submission_id=submission_id,
                    number=f"VT-2026-{len(self.issued):06d}",
                    degree=degree,
                    created=created,
                    file_url=f"/media/diplomas/{submission_id}.pdf",
                )
            )
        return tuple(recorded)


class RecordingNotifier:
    """Records the letters publication sent, one entry per recipient."""

    def __init__(self) -> None:
        self.letters: list[dict[str, object]] = []

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
        self.letters.append(
            {
                "email": email,
                "applicant_name": applicant_name,
                "competition_title": competition_title,
                "nomination_title": nomination_title,
                "results": tuple(results),
                "protocol_url": protocol_url,
            }
        )
