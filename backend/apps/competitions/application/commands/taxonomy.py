"""Use cases: competition taxonomy — categories (nominations), disciplines, age
categories and participant groups."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddAgeCategoryCommand,
    AddCategoryCommand,
    AddDisciplineCommand,
    AddParticipantGroupCommand,
    RemoveAgeCategoryCommand,
    RemoveCategoryCommand,
    RemoveDisciplineCommand,
    RemoveParticipantGroupCommand,
    RenameCategoryCommand,
    RenameDisciplineCommand,
)
from apps.competitions.application.dto.views import AddedChildResult, CompetitionDetailView
from apps.competitions.domain.value_objects import (
    AgeCategoryId,
    AgeRange,
    CategoryId,
    CategoryName,
    DisciplineId,
    DisciplineName,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipantGroupName,
)

from ._support import CompetitionCommandHandler

__all__ = [
    "AddAgeCategoryHandler",
    "AddCategoryHandler",
    "AddDisciplineHandler",
    "AddParticipantGroupHandler",
    "RemoveAgeCategoryHandler",
    "RemoveCategoryHandler",
    "RemoveDisciplineHandler",
    "RemoveParticipantGroupHandler",
    "RenameCategoryHandler",
    "RenameDisciplineHandler",
]


class AddCategoryHandler(CompetitionCommandHandler):
    """Add a category (nomination) to the competition."""

    def handle(self, command: AddCategoryCommand) -> AddedChildResult:
        competition = self._require(command.competition_id)
        category = competition.add_category(
            category_id=CategoryId.from_uuid(self._uuids.new()),
            name=CategoryName(command.name),
            now=self._clock.utcnow(),
        )
        return AddedChildResult(child_id=category.id.json(), competition=self._persist(competition))


class RenameCategoryHandler(CompetitionCommandHandler):
    """Rename an existing category."""

    def handle(self, command: RenameCategoryCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        competition.rename_category(
            category_id=CategoryId.from_string(command.category_id),
            name=CategoryName(command.name),
            now=self._clock.utcnow(),
        )
        return self._persist(competition)


class RemoveCategoryHandler(CompetitionCommandHandler):
    """Remove a category (refused while referenced)."""

    def handle(self, command: RemoveCategoryCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        competition.remove_category(category_id=CategoryId.from_string(command.category_id), now=self._clock.utcnow())
        return self._persist(competition)


class AddDisciplineHandler(CompetitionCommandHandler):
    """Add a discipline to a category."""

    def handle(self, command: AddDisciplineCommand) -> AddedChildResult:
        competition = self._require(command.competition_id)
        discipline = competition.add_discipline(
            discipline_id=DisciplineId.from_uuid(self._uuids.new()),
            category_id=CategoryId.from_string(command.category_id),
            name=DisciplineName(command.name),
            now=self._clock.utcnow(),
        )
        return AddedChildResult(child_id=discipline.id.json(), competition=self._persist(competition))


class RenameDisciplineHandler(CompetitionCommandHandler):
    """Rename an existing discipline."""

    def handle(self, command: RenameDisciplineCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        competition.rename_discipline(
            discipline_id=DisciplineId.from_string(command.discipline_id),
            name=DisciplineName(command.name),
            now=self._clock.utcnow(),
        )
        return self._persist(competition)


class RemoveDisciplineHandler(CompetitionCommandHandler):
    """Remove a discipline (refused while referenced by rules)."""

    def handle(self, command: RemoveDisciplineCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        competition.remove_discipline(discipline_id=DisciplineId.from_string(command.discipline_id), now=self._clock.utcnow())
        return self._persist(competition)


class AddAgeCategoryHandler(CompetitionCommandHandler):
    """Add an age band (overlapping ranges refused)."""

    def handle(self, command: AddAgeCategoryCommand) -> AddedChildResult:
        competition = self._require(command.competition_id)
        age_category = competition.add_age_category(
            age_category_id=AgeCategoryId.from_uuid(self._uuids.new()),
            age_range=AgeRange(command.min_age, command.max_age),
            now=self._clock.utcnow(),
        )
        return AddedChildResult(child_id=age_category.id.json(), competition=self._persist(competition))


class RemoveAgeCategoryHandler(CompetitionCommandHandler):
    """Remove an age band (refused while referenced by rules)."""

    def handle(self, command: RemoveAgeCategoryCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        competition.remove_age_category(age_category_id=AgeCategoryId.from_string(command.age_category_id), now=self._clock.utcnow())
        return self._persist(competition)


class AddParticipantGroupHandler(CompetitionCommandHandler):
    """Add a participant group to a category (overlapping count ranges refused)."""

    def handle(self, command: AddParticipantGroupCommand) -> AddedChildResult:
        competition = self._require(command.competition_id)
        group = competition.add_participant_group(
            participant_group_id=ParticipantGroupId.from_uuid(self._uuids.new()),
            category_id=CategoryId.from_string(command.category_id),
            name=ParticipantGroupName(command.name),
            count_range=ParticipantCountRange(command.min_count, command.max_count),
            now=self._clock.utcnow(),
        )
        return AddedChildResult(child_id=group.id.json(), competition=self._persist(competition))


class RemoveParticipantGroupHandler(CompetitionCommandHandler):
    """Remove a participant group (refused while referenced by rules)."""

    def handle(self, command: RemoveParticipantGroupCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        competition.remove_participant_group(
            participant_group_id=ParticipantGroupId.from_string(command.participant_group_id),
            now=self._clock.utcnow(),
        )
        return self._persist(competition)
