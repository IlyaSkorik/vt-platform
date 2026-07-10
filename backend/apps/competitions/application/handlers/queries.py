"""Query handlers for competitions."""

from __future__ import annotations

from apps.competitions.application.dto.queries import (
    GetCompetitionQuery,
    ListCompetitionsQuery,
)
from apps.competitions.application.dto.views import (
    CompetitionDetailView,
    CompetitionSummaryView,
)
from apps.competitions.application.interfaces import CompetitionRepository
from apps.competitions.domain.value_objects import CompetitionId, Season

__all__ = [
    "GetCompetitionHandler",
    "ListCompetitionsHandler",
]


class GetCompetitionHandler:
    """Return one competition."""

    def __init__(self, repository: CompetitionRepository) -> None:
        self._repository = repository

    def handle(
        self,
        query: GetCompetitionQuery,
    ) -> CompetitionDetailView:
        competition = self._repository.get(
            CompetitionId.from_string(query.competition_id),
        )

        if competition is None:
            raise LookupError(
                f"Competition {query.competition_id} not found.",
            )

        return CompetitionDetailView.of(
            competition,
        )


class ListCompetitionsHandler:
    """Return competitions."""

    def __init__(self, repository: CompetitionRepository) -> None:
        self._repository = repository

    def handle(
        self,
        query: ListCompetitionsQuery,
    ) -> list[CompetitionSummaryView]:
        if query.season is None:
            competitions = self._repository.list_all()
        else:
            competitions = self._repository.list_by_season(
                Season(query.season),
            )

        return [
            CompetitionSummaryView.of(
                competition,
            )
            for competition in competitions
        ]