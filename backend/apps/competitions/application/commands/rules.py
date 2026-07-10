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
from apps.competitions.domain.value_objects import Currency, Money

from ._support import CompetitionCommandHandler, combination_of

__all__ = [
    "AddAdmissionRuleHandler",
    "AddPricingRuleHandler",
    "ChangePriceHandler",
    "RemoveAdmissionRuleHandler",
    "RemovePricingRuleHandler",
]


class AddAdmissionRuleHandler(CompetitionCommandHandler):
    """Mark a combination admissible."""

    def handle(self, command: AddAdmissionRuleCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        events = competition.add_admission_rule(
            combination=combination_of(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format=command.participation_format,
            ),
            now=self._clock.utcnow(),
        )
        return self._persist(competition, events)


class RemoveAdmissionRuleHandler(CompetitionCommandHandler):
    """Remove an admission rule (refused while a pricing rule prices it)."""

    def handle(self, command: RemoveAdmissionRuleCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        events = competition.remove_admission_rule(
            combination=combination_of(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format=command.participation_format,
            ),
            now=self._clock.utcnow(),
        )
        return self._persist(competition, events)


class AddPricingRuleHandler(CompetitionCommandHandler):
    """Set the per-participant price for an admissible combination."""

    def handle(self, command: AddPricingRuleCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        events = competition.add_pricing_rule(
            combination=combination_of(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format=command.participation_format,
            ),
            price_per_participant=Money.of(command.amount, Currency(command.currency)),
            now=self._clock.utcnow(),
        )
        return self._persist(competition, events)


class ChangePriceHandler(CompetitionCommandHandler):
    """Change the per-participant price of an existing pricing rule."""

    def handle(self, command: ChangePriceCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        events = competition.change_price(
            combination=combination_of(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format=command.participation_format,
            ),
            price_per_participant=Money.of(command.amount, Currency(command.currency)),
            now=self._clock.utcnow(),
        )
        return self._persist(competition, events)


class RemovePricingRuleHandler(CompetitionCommandHandler):
    """Remove a pricing rule."""

    def handle(self, command: RemovePricingRuleCommand) -> CompetitionDetailView:
        competition = self._require(command.competition_id)
        events = competition.remove_pricing_rule(
            combination=combination_of(
                category_id=command.category_id,
                discipline_id=command.discipline_id,
                age_category_id=command.age_category_id,
                participant_group_id=command.participant_group_id,
                participation_format=command.participation_format,
            ),
            now=self._clock.utcnow(),
        )
        return self._persist(competition, events)
