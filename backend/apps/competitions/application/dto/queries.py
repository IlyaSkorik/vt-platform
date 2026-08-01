"""Query DTOs for the Competitions bounded context.

Input shapes for read use cases (application/queries/). Framework-neutral, frozen,
slotted dataclasses carrying only primitives.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GetCompetitionQuery", "ListCompetitionsQuery"]


@dataclass(frozen=True, slots=True)
class GetCompetitionQuery:
    """Fetch a single competition's full detail by id."""

    competition_id: str


@dataclass(frozen=True, slots=True)
class ListCompetitionsQuery:
    """List competitions, optionally narrowed to one season and one organizer.

    ``organizer_id`` is the scoping filter, not a convenience: the organizer
    workspace passes the caller's own organization so a festival run by another
    organization never appears in it. ``None`` means "every organizer", which only
    the platform operator's own reads ask for.
    """

    season: str | None = None
    organizer_id: str | None = None
