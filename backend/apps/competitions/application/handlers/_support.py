from __future__ import annotations

from abc import ABC

from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.application.interfaces import (
    Clock,
    CompetitionRepository,
    EventPublisher,
    UuidGenerator,
)
from apps.competitions.domain.entities import Competition
from apps.competitions.domain.events import DomainEvent
from backend.apps.competitions.domain.value_objects import AdmissionCombination, AgeCategoryId, CategoryId, DisciplineId, ParticipantGroupId, ParticipationFormat


class CompetitionCommandHandler(ABC):
    """Base class for Competition command handlers."""

    __slots__ = (
        "_repository",
        "_clock",
        "_publisher",
        "_uuids",
    )

    def __init__(
        self,
        *,
        repository: CompetitionRepository,
        clock: Clock,
        publisher: EventPublisher,
        uuids: UuidGenerator,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._publisher = publisher
        self._uuids = uuids

    def _persist(
        self,
        competition: Competition,
        events: list[DomainEvent],
    ) -> CompetitionDetailView:
        self._repository.save(competition)

        if events:
            self._publisher.publish(events)

        return CompetitionDetailView.of(competition)
    
    def _combination(
        self,
        *,
        category_id: str,
        discipline_id: str,
        age_category_id: str,
        participant_group_id: str,
        participation_format: str,
    ) -> AdmissionCombination:
        return AdmissionCombination(
            category_id=CategoryId.from_string(category_id),
            discipline_id=DisciplineId.from_string(discipline_id),
            age_category_id=AgeCategoryId.from_string(age_category_id),
            participant_group_id=ParticipantGroupId.from_string(participant_group_id),
            participation_format=ParticipationFormat(participation_format),
        )