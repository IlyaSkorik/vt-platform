"""Admission & pricing rule child rows of the :class:`Competition` aggregate.

Persistence only (ARCH-001 §7.2, §14). Admission and pricing rules are domain
*value objects* keyed by an :class:`AdmissionCombination` (a five-part key), but in
the database each is a row carrying the combination's five columns plus, for
pricing, the per-participant price. The combination columns are plain UUID / enum
columns (the aggregate root owns their referential integrity). Rows are
synchronized wholesale by the repository under the root's optimistic lock, so the
synthetic ``id`` primary key is regenerated on each save and is never surfaced to
the domain, which identifies a rule by its combination alone.
"""

from __future__ import annotations

from django.db import models

from apps.competitions.domain.value_objects import Currency, ParticipationFormat

from .base import BasePersistenceModel

__all__ = ["AdmissionRuleModel", "PricingRuleModel"]

_FORMAT_CHOICES = [(f.value, f.name.title()) for f in ParticipationFormat]
_CURRENCY_CHOICES = [(c.value, c.value) for c in Currency]


class AdmissionRuleModel(BasePersistenceModel):
    """Database row for an admission rule — one admissible combination (persistence only)."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="admission_rules",
    )
    category_id = models.UUIDField()
    discipline_id = models.UUIDField()
    age_category_id = models.UUIDField()
    participant_group_id = models.UUIDField()
    participation_format = models.CharField(max_length=16, choices=_FORMAT_CHOICES)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_admission_rule"
        verbose_name = "admission rule"
        verbose_name_plural = "admission rules"
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["competition", "category_id", "discipline_id", "age_category_id", "participant_group_id", "participation_format"],
                name="competitions_unique_admission_combination",
            ),
        ]

    def __str__(self) -> str:
        return f"admission {self.id}"


class PricingRuleModel(BasePersistenceModel):
    """Database row for a pricing rule — the per-participant price of a combination."""

    competition = models.ForeignKey(
        "competitions.CompetitionModel",
        on_delete=models.CASCADE,
        related_name="pricing_rules",
    )
    category_id = models.UUIDField()
    discipline_id = models.UUIDField()
    age_category_id = models.UUIDField()
    participant_group_id = models.UUIDField()
    participation_format = models.CharField(max_length=16, choices=_FORMAT_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=_CURRENCY_CHOICES, default=Currency.RUB.value)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_pricing_rule"
        verbose_name = "pricing rule"
        verbose_name_plural = "pricing rules"
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["competition", "category_id", "discipline_id", "age_category_id", "participant_group_id", "participation_format"],
                name="competitions_unique_pricing_combination",
            ),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="competitions_pricing_amount_non_negative"),
        ]

    def __str__(self) -> str:
        return f"pricing {self.id} @ {self.amount} {self.currency}"
