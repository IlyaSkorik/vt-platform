"""Use cases: admission & pricing rules."""

from __future__ import annotations

from apps.competitions.application.dto.commands import (
    AddAdmissionRuleCommand,
    AddPricingRuleCommand,
    ChangePriceCommand,
    RemoveAdmissionRuleCommand,
    RemovePricingRuleCommand,
)
from apps.competitions.application.dto.views import CompetitionDetailView
from apps.competitions.application.handlers._support import CompetitionCommandHandler
from apps.competitions.domain.value_objects import PricingCalculationType

__all__ = (
    "AddAdmissionRuleHandler",
    "AddPricingRuleHandler",
    "ChangePriceHandler",
    "RemoveAdmissionRuleHandler",
    "RemovePricingRuleHandler",
)


class AddAdmissionRuleHandler(CompetitionCommandHandler):
    """Add an admission rule."""

    def handle(
        self,
        command: AddAdmissionRuleCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.add_admission_rule(
            combination=self._combination(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format_id=command.participation_format_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class RemoveAdmissionRuleHandler(CompetitionCommandHandler):
    """Remove an admission rule."""

    def handle(
        self,
        command: RemoveAdmissionRuleCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.remove_admission_rule(
            combination=self._combination(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format_id=command.participation_format_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class AddPricingRuleHandler(CompetitionCommandHandler):
    """Add a pricing rule."""

    def handle(
        self,
        command: AddPricingRuleCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.add_pricing_rule(
            combination=self._combination(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format_id=command.participation_format_id,
            ),
            price_per_participant=self._money(
                amount=command.amount,
                currency=command.currency,
            ),
            calculation_type=self._pricing_calculation_type(command.calculation_type) or PricingCalculationType.PER_PARTICIPANT,
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class ChangePriceHandler(CompetitionCommandHandler):
    """Change the price of an existing pricing rule."""

    def handle(
        self,
        command: ChangePriceCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.change_price(
            combination=self._combination(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format_id=command.participation_format_id,
            ),
            price_per_participant=self._money(
                amount=command.amount,
                currency=command.currency,
            ),
            calculation_type=self._pricing_calculation_type(command.calculation_type),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)


class RemovePricingRuleHandler(CompetitionCommandHandler):
    """Remove a pricing rule."""

    def handle(
        self,
        command: RemovePricingRuleCommand,
    ) -> CompetitionDetailView:
        competition = self._require(command.competition_id)

        events = competition.remove_pricing_rule(
            combination=self._combination(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format_id=command.participation_format_id,
            ),
            now=self._clock.utcnow(),
        )

        return self._persist(competition, events)
