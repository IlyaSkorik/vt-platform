"""ACL adapters over the Competition context.

Two adapters back the application's Competition ports by loading the ``Competition``
aggregate through its repository and projecting exactly the slice each port needs:

* :class:`DjangoCompetitionCatalog` - existence, whether applications are open now,
  the participation policy (admissibility + participant-group count band) and the
  list-price quote for a combination.
* :class:`DjangoCompetitionServiceCatalog` - additional-service quotes and the
  competition's required consent codes.

**Vocabulary bridge.** The Applications context calls the first configuration axis a
*nomination*; the Competition context calls it a *category*. This adapter maps
``nomination_id -> category_id`` when assembling the Competition's
:class:`AdmissionCombination`. All ids are UUID v7 values wrapped in per-context
types, so translation is a ``.value`` round-trip.
"""

from __future__ import annotations

from datetime import datetime

from apps.applications.application.interfaces import AdditionalServiceQuote
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    CompetitionId,
    CompetitionPriceQuote,
    Currency,
    DisciplineId,
    Money,
    NominationId,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipationFormatId,
    PriceCalculationType,
    ServiceId,
    SubmissionParticipationPolicy,
)
from apps.competitions.domain.entities import Competition
from apps.competitions.domain.value_objects import (
    AdmissionCombination,
)
from apps.competitions.domain.value_objects import (
    AgeCategoryId as CompAgeCategoryId,
)
from apps.competitions.domain.value_objects import (
    CategoryId as CompCategoryId,
)
from apps.competitions.domain.value_objects import (
    CompetitionId as CompCompetitionId,
)
from apps.competitions.domain.value_objects import (
    DisciplineId as CompDisciplineId,
)
from apps.competitions.domain.value_objects import (
    Money as CompMoney,
)
from apps.competitions.domain.value_objects import (
    ParticipantGroupId as CompParticipantGroupId,
)
from apps.competitions.domain.value_objects import (
    ParticipationFormatId as CompParticipationFormatId,
)
from apps.competitions.infrastructure.repositories.django_competition_repository import DjangoCompetitionRepository

__all__ = ["DjangoCompetitionCatalog", "DjangoCompetitionServiceCatalog"]


def _to_money(amount: CompMoney) -> Money:
    """Translate a Competition ``Money`` into this context's ``Money`` (by value)."""
    return Money.of(str(amount.amount), Currency(amount.currency.value))


def _combination(
    *,
    nomination_id: NominationId,
    discipline_id: DisciplineId,
    age_category_id: AgeCategoryId,
    participant_group_id: ParticipantGroupId,
    participation_format_id: ParticipationFormatId,
) -> AdmissionCombination:
    """Assemble the Competition's five-axis combination (nomination -> category)."""
    return AdmissionCombination(
        category_id=CompCategoryId.from_uuid(nomination_id.value),
        discipline_id=CompDisciplineId.from_uuid(discipline_id.value),
        age_category_id=CompAgeCategoryId.from_uuid(age_category_id.value),
        participant_group_id=CompParticipantGroupId.from_uuid(participant_group_id.value),
        participation_format_id=CompParticipationFormatId.from_uuid(participation_format_id.value),
    )


class DjangoCompetitionCatalog:
    """Competition ACL implementing the ``CompetitionCatalog`` port."""

    def __init__(self) -> None:
        self._repo = DjangoCompetitionRepository()

    def _load(self, competition_id: CompetitionId) -> Competition | None:
        return self._repo.get(CompCompetitionId.from_uuid(competition_id.value))

    def exists(self, competition_id: CompetitionId) -> bool:
        return self._repo.exists(CompCompetitionId.from_uuid(competition_id.value))

    def accepts_submissions(self, *, competition_id: CompetitionId, now: datetime) -> bool:
        competition = self._load(competition_id)
        return competition is not None and competition.is_application_allowed(now)

    def participation_policy(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: NominationId,
        discipline_id: DisciplineId,
        age_category_id: AgeCategoryId,
        participant_group_id: ParticipantGroupId,
        participation_format_id: ParticipationFormatId,
    ) -> SubmissionParticipationPolicy | None:
        competition = self._load(competition_id)
        if competition is None:
            return None
        group = next((g for g in competition.participant_groups if g.id.value == participant_group_id.value), None)
        if group is None:
            return None
        combination = _combination(
            nomination_id=nomination_id,
            discipline_id=discipline_id,
            age_category_id=age_category_id,
            participant_group_id=participant_group_id,
            participation_format_id=participation_format_id,
        )
        count_range = ParticipantCountRange(min_count=group.count_range.min_count, max_count=group.count_range.max_count)
        return SubmissionParticipationPolicy(participant_count_range=count_range, is_admissible=competition.is_admissible(combination))

    def price_quote(
        self,
        *,
        competition_id: CompetitionId,
        nomination_id: NominationId,
        discipline_id: DisciplineId,
        age_category_id: AgeCategoryId,
        participant_group_id: ParticipantGroupId,
        participation_format_id: ParticipationFormatId,
    ) -> CompetitionPriceQuote | None:
        competition = self._load(competition_id)
        if competition is None:
            return None
        combination = _combination(
            nomination_id=nomination_id,
            discipline_id=discipline_id,
            age_category_id=age_category_id,
            participant_group_id=participant_group_id,
            participation_format_id=participation_format_id,
        )
        unit_price = competition.price_for(combination)
        if unit_price is None:
            return None
        rule = competition.pricing_rule_for(combination)
        calculation_type = PriceCalculationType(rule.calculation_type.value) if rule is not None else PriceCalculationType.PER_PARTICIPANT
        return CompetitionPriceQuote(unit_price=_to_money(unit_price), calculation_type=calculation_type)


class DjangoCompetitionServiceCatalog:
    """Competition ACL implementing the ``CompetitionServiceCatalog`` port."""

    def __init__(self) -> None:
        self._repo = DjangoCompetitionRepository()

    def get_additional_service(self, *, competition_id: CompetitionId, service_id: ServiceId) -> AdditionalServiceQuote | None:
        competition = self._repo.get(CompCompetitionId.from_uuid(competition_id.value))
        if competition is None:
            return None
        service = next((s for s in competition.additional_services if s.id.value == service_id.value), None)
        if service is None or not service.is_enabled:
            return None
        return AdditionalServiceQuote(service_id=service_id, name=service.name.value, unit_price=_to_money(service.price))

    def required_consent_codes(self, *, competition_id: CompetitionId) -> frozenset[str]:
        # The Competition context does not model required consents yet; none are
        # mandated. Consents recorded on an application are still preserved.
        return frozenset()
