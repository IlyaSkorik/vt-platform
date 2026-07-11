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
    Currency,
    DisciplineId,
    Money,
    ParticipantGroupId,
    ParticipationFormat,
)


class CompetitionCommandHandler:
    """Base class for Competition command handlers.

    Centralises the boilerplate every command use case shares: constructor
    injection of the outbound ports, loading the aggregate (``_require``),
    building common value objects, and persisting-then-publishing (``_persist``).
    Concrete handlers depend only on the ports; the composition root binds the
    adapters. Structurally there is no framework here.
    """

    __slots__ = (
        "_clock",
        "_publisher",
        "_repository",
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

    def _require(self, competition_id: str) -> Competition:
        """Load the competition or raise :class:`CompetitionNotFoundError`."""
        competition = self._repository.get(CompetitionId.from_string(competition_id))
        if competition is None:
            raise CompetitionNotFoundError(f"No competition {competition_id}.")
        return competition

    def _persist(
        self,
        competition: Competition,
        events: Sequence[DomainEvent] = (),
    ) -> CompetitionDetailView:
        self._repository.save(competition)

        if events:
            self._publisher.publish(events)

        return CompetitionDetailView.of(competition)

    def _money(self, *, amount: str, currency: str) -> Money:
        return Money.of(amount, Currency(currency))

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
