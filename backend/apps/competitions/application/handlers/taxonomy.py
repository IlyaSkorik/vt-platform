"""Use cases: competition taxonomy."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddAgeCategoryCommand,
    AddCategoryCommand,
    AddDisciplineCommand,
    AddParticipantGroupCommand,
    DisableNominationWaitlistCommand,
    EnableNominationWaitlistCommand,
    RemoveAgeCategoryCommand,
    RemoveCategoryCommand,
    RemoveDisciplineCommand,
    RemoveParticipantGroupCommand,
    RenameCategoryCommand,
    RenameDisciplineCommand,
    ResumeNominationRegistrationCommand,
    ScheduleNominationRegistrationCommand,
    StopNominationRegistrationCommand,
    UpdateAgeCategoryCommand,
    UpdateParticipantGroupCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.domain.entities import _SENTINEL, _Unset
from apps.competitions.domain.value_objects import (
    AgeCategoryId,
    AgeCategoryName,
    AgeCategoryType,
    AgeRange,
    CategoryDescription,
    CategoryId,
    CategoryName,
    DisciplineId,
    DisciplineName,
    MixedAgeCalculationMethod,
    ParticipantCountRange,
    ParticipantGroupDescription,
    ParticipantGroupId,
    ParticipantGroupName,
)

from ._support import CompetitionCommandHandler

__all__ = (
    "AddAgeCategoryHandler",
    "AddCategoryHandler",
    "AddDisciplineHandler",
    "AddParticipantGroupHandler",
    "DisableNominationWaitlistHandler",
    "EnableNominationWaitlistHandler",
    "RemoveAgeCategoryHandler",
    "RemoveCategoryHandler",
    "RemoveDisciplineHandler",
    "RemoveParticipantGroupHandler",
    "RenameCategoryHandler",
    "RenameDisciplineHandler",
    "ResumeNominationRegistrationHandler",
    "ScheduleNominationRegistrationHandler",
    "StopNominationRegistrationHandler",
    "UpdateAgeCategoryHandler",
    "UpdateParticipantGroupHandler",
)


class AddCategoryHandler(CompetitionCommandHandler):
    """Add a category."""

    def handle(
        self,
        command: AddCategoryCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.add_category(
            category_id=CategoryId.from_uuid(self._uuids.new()),
            name=CategoryName(command.name),
            now=self._clock.utcnow(),
            description=CategoryDescription(command.description) if command.description is not None else None,
            sort_order=command.sort_order,
            held_at=command.held_at,
        )

        return self._persist(competition)


class RenameCategoryHandler(CompetitionCommandHandler):
    """Update a category (partial: name, description, sort_order)."""

    def handle(
        self,
        command: RenameCategoryCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.rename_category(
            category_id=CategoryId.from_string(command.category_id),
            name=CategoryName(command.name) if command.name is not None else None,
            description=CategoryDescription(command.description) if command.description is not None else None,
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class RemoveCategoryHandler(CompetitionCommandHandler):
    """Remove a category."""

    def handle(
        self,
        command: RemoveCategoryCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.remove_category(
            category_id=CategoryId.from_string(command.category_id),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class ScheduleNominationRegistrationHandler(CompetitionCommandHandler):
    """Set (or replace) a nomination's registration window (open/close instants)."""

    def handle(
        self,
        command: ScheduleNominationRegistrationCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.schedule_nomination_registration(
            category_id=CategoryId.from_string(command.category_id),
            opens_at=command.opens_at,
            closes_at=command.closes_at,
            held_at=command.held_at,
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class StopNominationRegistrationHandler(CompetitionCommandHandler):
    """Stop a nomination's registration early."""

    def handle(
        self,
        command: StopNominationRegistrationCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.stop_nomination_registration(
            category_id=CategoryId.from_string(command.category_id),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class ResumeNominationRegistrationHandler(CompetitionCommandHandler):
    """Resume a previously stopped nomination's registration."""

    def handle(
        self,
        command: ResumeNominationRegistrationCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.resume_nomination_registration(
            category_id=CategoryId.from_string(command.category_id),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class EnableNominationWaitlistHandler(CompetitionCommandHandler):
    """Keep a waitlist for a nomination once its registration closes."""

    def handle(
        self,
        command: EnableNominationWaitlistCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.enable_nomination_waitlist(
            category_id=CategoryId.from_string(command.category_id),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class DisableNominationWaitlistHandler(CompetitionCommandHandler):
    """Stop taking waitlist entries for a nomination; those already queued remain."""

    def handle(
        self,
        command: DisableNominationWaitlistCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.disable_nomination_waitlist(
            category_id=CategoryId.from_string(command.category_id),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class AddDisciplineHandler(CompetitionCommandHandler):
    """Add a discipline."""

    def handle(
        self,
        command: AddDisciplineCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.add_discipline(
            discipline_id=DisciplineId.from_uuid(self._uuids.new()),
            category_id=CategoryId.from_string(command.category_id),
            name=DisciplineName(command.name),
            now=self._clock.utcnow(),
            sort_order=command.sort_order,
        )

        return self._persist(competition)


class RenameDisciplineHandler(CompetitionCommandHandler):
    """Update a discipline (partial: name, sort_order)."""

    def handle(
        self,
        command: RenameDisciplineCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.rename_discipline(
            discipline_id=DisciplineId.from_string(command.discipline_id),
            name=DisciplineName(command.name) if command.name is not None else None,
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class RemoveDisciplineHandler(CompetitionCommandHandler):
    """Remove a discipline."""

    def handle(
        self,
        command: RemoveDisciplineCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.remove_discipline(
            discipline_id=DisciplineId.from_string(command.discipline_id),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class AddAgeCategoryHandler(CompetitionCommandHandler):
    """Add an age category."""

    def handle(
        self,
        command: AddAgeCategoryCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.add_age_category(
            age_category_id=AgeCategoryId.from_uuid(self._uuids.new()),
            participant_group_id=ParticipantGroupId.from_string(command.participant_group_id),
            name=AgeCategoryName(command.name),
            age_range=AgeRange(
                min_age=command.min_age,
                max_age=command.max_age,
            ),
            now=self._clock.utcnow(),
            age_category_type=AgeCategoryType(command.age_category_type),
            mixed_calculation_method=(
                MixedAgeCalculationMethod(command.mixed_calculation_method) if command.mixed_calculation_method is not None else None
            ),
            sort_order=command.sort_order,
        )

        return self._persist(competition)


class UpdateAgeCategoryHandler(CompetitionCommandHandler):
    """Update an age category (partial: name, age_range, type, method, sort_order)."""

    def handle(
        self,
        command: UpdateAgeCategoryCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        age_range: AgeRange | None = None
        if command.min_age is not None and command.max_age is not None:
            age_range = AgeRange(min_age=command.min_age, max_age=command.max_age)

        # `mixed_calculation_method` is the one field where "not mentioned in this
        # request" and "explicitly cleared" mean different things, which is exactly what
        # the domain's sentinel default expresses. Passing it directly replaces a
        # dynamically built `**kwargs` dict that no checker could match to the method's
        # parameters — the conditional omission was the only reason for the dict.
        mixed_method: MixedAgeCalculationMethod | None | _Unset = _SENTINEL
        if command.age_category_type is not None or command.mixed_calculation_method is not None:
            mixed_method = MixedAgeCalculationMethod(command.mixed_calculation_method) if command.mixed_calculation_method is not None else None

        competition.update_age_category(
            age_category_id=AgeCategoryId.from_string(command.age_category_id),
            name=AgeCategoryName(command.name) if command.name is not None else None,
            age_range=age_range,
            age_category_type=AgeCategoryType(command.age_category_type) if command.age_category_type is not None else None,
            mixed_calculation_method=mixed_method,
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class RemoveAgeCategoryHandler(CompetitionCommandHandler):
    """Remove an age category."""

    def handle(
        self,
        command: RemoveAgeCategoryCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.remove_age_category(
            age_category_id=AgeCategoryId.from_string(
                command.age_category_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class AddParticipantGroupHandler(CompetitionCommandHandler):
    """Add a participant group."""

    def handle(
        self,
        command: AddParticipantGroupCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        description = None
        if command.description is not None and command.description.strip():
            description = ParticipantGroupDescription(command.description)

        competition.add_participant_group(
            participant_group_id=ParticipantGroupId.from_uuid(
                self._uuids.new(),
            ),
            name=ParticipantGroupName(
                command.name,
            ),
            count_range=ParticipantCountRange(
                min_count=command.min_count,
                max_count=command.max_count,
            ),
            now=self._clock.utcnow(),
            description=description,
            sort_order=command.sort_order,
        )

        return self._persist(competition)


class UpdateParticipantGroupHandler(CompetitionCommandHandler):
    """Update a participant group (partial: name, range, description, sort_order)."""

    def handle(
        self,
        command: UpdateParticipantGroupCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        count_range: ParticipantCountRange | None = None
        if command.min_count is not None:
            count_range = ParticipantCountRange(
                min_count=command.min_count,
                max_count=command.max_count,
            )

        # Typed as the union the domain actually accepts, rather than `object` behind a
        # silenced argument: `update_description` false means "leave it alone", which is
        # a different request from "clear it", and the sentinel is what says so.
        description: ParticipantGroupDescription | None | _Unset = _SENTINEL
        if command.update_description:
            description = (
                ParticipantGroupDescription(command.description) if command.description is not None and command.description.strip() else None
            )

        competition.update_participant_group(
            participant_group_id=ParticipantGroupId.from_string(command.participant_group_id),
            name=ParticipantGroupName(command.name) if command.name is not None else None,
            count_range=count_range,
            description=description,
            sort_order=command.sort_order,
            now=self._clock.utcnow(),
        )

        return self._persist(competition)


class RemoveParticipantGroupHandler(CompetitionCommandHandler):
    """Remove a participant group."""

    def handle(
        self,
        command: RemoveParticipantGroupCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        competition.remove_participant_group(
            participant_group_id=ParticipantGroupId.from_string(
                command.participant_group_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition)
