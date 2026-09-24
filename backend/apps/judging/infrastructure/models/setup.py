"""Persistence for the Judging configuration (persistence only, ARCH-001 §7.2).

One row per competition. The configuration is held in JSON columns rather than in a
table per concept, and that is a deliberate trade: criteria, award tiers and board
settings are edited wholesale by one screen, read wholesale by everything else, and
never queried across competitions. Four child tables would buy joins nobody performs
and cost a migration every time an organizer wants another knob.

``competition_id`` is a plain UUID column, not a foreign key: cross-context references
are held as ids and resolved through the owning context's interface (ARCH-001 §7.2).
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["JudgingSetupModel"]


class JudgingSetupModel(BasePersistenceModel):
    """Database row for one competition's judging configuration."""

    competition_id = models.UUIDField(unique=True)
    #: ``[{"code", "label", "min_score", "max_score", "sort_order"}, ...]``
    award_scale = models.JSONField(default=list)
    #: ``[{"scope", "target_id", "criteria": [...]}, ...]``
    criteria_sets = models.JSONField(default=list)
    #: ``{"aggregation", "drop_highest", "drop_lowest"}``
    scoring_rules = models.JSONField(default=dict)
    #: ``["CATEGORY", "AGE_CATEGORY", ...]``
    tally_dimensions = models.JSONField(default=list)
    #: ``{"enabled", "visibility", "reveal", "show_award", "show_running_order"}``
    board = models.JSONField(default=dict)
    #: Minted once, when the board is first switched on, and permanent from then on.
    board_slug = models.CharField(max_length=64, null=True, blank=True, default=None, unique=True)

    class Meta(BasePersistenceModel.Meta):
        db_table = "judging_setup"
        verbose_name = "judging setup"
        verbose_name_plural = "judging setups"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
        ]

    def __str__(self) -> str:
        return f"Судейство {self.competition_id}"
