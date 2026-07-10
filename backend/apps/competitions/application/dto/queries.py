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
    """List competitions, optionally narrowed to one season."""

    season: str | None = None
