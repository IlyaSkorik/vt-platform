"""Shared scaffolding for Competitions command handlers.

One use case = one business operation and one transaction boundary (ARCH-001 §7.2,
§7.4). Every command handler loads the aggregate, invokes a single domain method,
persists the whole aggregate, publishes the events the domain produced, and returns
a fresh view. The tiny base class here removes that boilerplate so each concrete
handler is just its domain call.
"""

from __future__ import annotations

from collections.abc import Sequence

from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.application.exceptions import CompetitionNotFoundError
from apps.competitions.application.interfaces import (
    Clock,
    CompetitionRepository,
    EventPublisher,
    UuidGenerator,
)
from apps.competitions.domain.entities import Competition
from apps.competitions.domain.events import DomainEvent
from apps.competitions.domain.value_objects import (
    AdmissionCombination,
    AgeCategoryId,
    CategoryId,
    CompetitionId,
    DisciplineId,
    ParticipantGroupId,
    ParticipationFormat,
)

__all__ = ["CompetitionCommandHandler", "combination_of"]


class CompetitionCommandHandler:
    """Base for command handlers: injects the ports and centralises load/persist.

    Concrete handlers depend only on the application ports (repository, clock,
    uuid generator, event publisher); the composition root binds the concrete
    adapters. Structurally there is no framework here.
    """

    def __init__(
        self,
        *,
        competitions: CompetitionRepository,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._competitions = competitions
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def _require(self, competition_id: str) -> Competition:
        """Load the competition or raise :class:`CompetitionNotFoundError`."""
        competition = self._competitions.get(CompetitionId.from_string(competition_id))
        if competition is None:
            raise CompetitionNotFoundError(f"No competition {competition_id}.")
        return competition

    def _persist(self, competition: Competition, events: Sequence[DomainEvent] = ()) -> CompetitionDetailView:
        """Save the aggregate, publish its events, and project a fresh detail view."""
        self._competitions.save(competition)
        if events:
            self._events.publish(events)
        return CompetitionDetailView.of(competition)


def combination_of(
    *,
    category_id: str,
    discipline_id: str,
    age_category_id: str,
    participant_group_id: str,
    participation_format: str,
) -> AdmissionCombination:
    """Build an :class:`AdmissionCombination` from its five string parts."""
    return AdmissionCombination(
        category_id=CategoryId.from_string(category_id),
        discipline_id=DisciplineId.from_string(discipline_id),
        age_category_id=AgeCategoryId.from_string(age_category_id),
        participant_group_id=ParticipantGroupId.from_string(participant_group_id),
        participation_format=ParticipationFormat(participation_format),
    )
