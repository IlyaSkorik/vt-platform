"""Translation between :class:`JudgingSetup` and its database row.

The one place JSON shapes are read, and it is defensive on purpose: every value goes
through a default and an unreadable entry is skipped rather than raised on. A festival
whose configuration was written by an older version of this code, or hand-edited in the
admin, must still open its screen — an organizer cannot fix a criteria sheet they
cannot load.

Scores are stored as **strings**. JSON numbers are binary floats, and a band that was
typed as ``9.1`` and comes back as ``9.099999999999999`` is a band that stops matching
the score it was written for.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.judging.domain.entities import JudgingSetup
from apps.judging.domain.exceptions import InvalidJudgingDataError
from apps.judging.domain.value_objects import (
    AggregationMethod,
    AwardScale,
    AwardTier,
    BoardReveal,
    BoardSettings,
    BoardVisibility,
    CriteriaScope,
    CriteriaSet,
    Criterion,
    ScoringRules,
    TallyDimension,
    TallyScope,
)
from apps.judging.infrastructure.models import JudgingSetupModel

__all__ = ["setup_to_model", "to_setup"]


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _award_scale(raw: Any) -> AwardScale:
    if not isinstance(raw, list) or not raw:
        return AwardScale.default()
    tiers: list[AwardTier] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        try:
            tiers.append(
                AwardTier(
                    code=str(item.get("code", "")),
                    label=str(item.get("label", "")),
                    min_score=_decimal(item.get("min_score")),
                    max_score=_decimal(item.get("max_score")),
                    sort_order=int(item.get("sort_order", index) or 0),
                )
            )
        except (InvalidJudgingDataError, TypeError, ValueError):
            continue
    if not tiers:
        return AwardScale.default()
    try:
        return AwardScale(tiers=tuple(tiers))
    except InvalidJudgingDataError:
        # A stored scale whose bands overlap: keep the names, drop the bands rather
        # than refuse to open the screen the organizer needs in order to fix it.
        return AwardScale(tiers=tuple(AwardTier(code=tier.code, label=tier.label, sort_order=tier.sort_order) for tier in tiers))


def _criteria_sets(raw: Any) -> tuple[CriteriaSet, ...]:
    if not isinstance(raw, list):
        return ()
    sets: list[CriteriaSet] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        target_id = _uuid(item.get("target_id"))
        if target_id is None:
            continue
        try:
            scope = CriteriaScope(str(item.get("scope", CriteriaScope.CATEGORY.value)))
        except ValueError:
            continue
        criteria: list[Criterion] = []
        for index, entry in enumerate(item.get("criteria", []) if isinstance(item.get("criteria"), list) else []):
            if not isinstance(entry, dict):
                continue
            criterion_id = _uuid(entry.get("id"))
            max_score = _decimal(entry.get("max_score"))
            weight = _decimal(entry.get("weight"))
            if criterion_id is None or max_score is None or weight is None:
                continue
            try:
                criteria.append(
                    Criterion(
                        id=criterion_id,
                        name=str(entry.get("name", "")),
                        max_score=max_score,
                        weight=weight,
                        sort_order=int(entry.get("sort_order", index) or 0),
                        description=entry.get("description"),
                    )
                )
            except (InvalidJudgingDataError, TypeError, ValueError):
                continue
        if criteria:
            sets.append(CriteriaSet(scope=scope, target_id=target_id, criteria=tuple(criteria)))
    return tuple(sets)


def _scoring_rules(raw: Any) -> ScoringRules:
    if not isinstance(raw, dict):
        return ScoringRules()
    try:
        aggregation = AggregationMethod(str(raw.get("aggregation", AggregationMethod.AVERAGE.value)))
    except ValueError:
        aggregation = AggregationMethod.AVERAGE
    return ScoringRules(
        aggregation=aggregation,
        drop_highest=bool(raw.get("drop_highest", False)),
        drop_lowest=bool(raw.get("drop_lowest", False)),
    )


def _tally_scope(raw: Any) -> TallyScope:
    if not isinstance(raw, list):
        return TallyScope.default()
    dimensions: set[TallyDimension] = set()
    for value in raw:
        try:
            dimensions.add(TallyDimension(str(value)))
        except ValueError:
            continue
    return TallyScope(dimensions=frozenset(dimensions)) if dimensions else TallyScope.default()


def _board(raw: Any) -> BoardSettings:
    if not isinstance(raw, dict):
        return BoardSettings()
    try:
        visibility = BoardVisibility(str(raw.get("visibility", BoardVisibility.TOTAL_ONLY.value)))
    except ValueError:
        visibility = BoardVisibility.TOTAL_ONLY
    try:
        reveal = BoardReveal(str(raw.get("reveal", BoardReveal.AFTER_CLOSE.value)))
    except ValueError:
        reveal = BoardReveal.AFTER_CLOSE
    return BoardSettings(
        enabled=bool(raw.get("enabled", False)),
        visibility=visibility,
        reveal=reveal,
        show_award=bool(raw.get("show_award", True)),
        show_running_order=bool(raw.get("show_running_order", True)),
    )


def to_setup(model: JudgingSetupModel) -> JudgingSetup:
    """Rebuild the aggregate from its row."""
    return JudgingSetup.rehydrate(
        setup_id=model.id,
        competition_id=model.competition_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        award_scale=_award_scale(model.award_scale),
        criteria_sets=_criteria_sets(model.criteria_sets),
        scoring_rules=_scoring_rules(model.scoring_rules),
        tally_scope=_tally_scope(model.tally_dimensions),
        board=_board(model.board),
        board_slug=model.board_slug or None,
        version=model.version,
    )


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def _tier_json(tier: AwardTier) -> dict[str, Any]:
    return {
        "code": tier.code,
        "label": tier.label,
        "min_score": str(tier.min_score) if tier.min_score is not None else None,
        "max_score": str(tier.max_score) if tier.max_score is not None else None,
        "sort_order": tier.sort_order,
    }


def _criteria_set_json(item: CriteriaSet) -> dict[str, Any]:
    return {
        "scope": item.scope.value,
        "target_id": str(item.target_id),
        "criteria": [
            {
                "id": str(criterion.id),
                "name": criterion.name,
                "max_score": str(criterion.max_score),
                "weight": str(criterion.weight),
                "sort_order": criterion.sort_order,
                "description": criterion.description,
            }
            for criterion in item.criteria
        ],
    }


def setup_to_model(setup: JudgingSetup) -> dict[str, Any]:
    """The column values for ``setup``, ready for ``update_or_create``."""
    return {
        "competition_id": setup.competition_id,
        "award_scale": [_tier_json(tier) for tier in setup.award_scale.tiers],
        "criteria_sets": [_criteria_set_json(item) for item in setup.criteria_sets],
        "scoring_rules": {
            "aggregation": setup.scoring_rules.aggregation.value,
            "drop_highest": setup.scoring_rules.drop_highest,
            "drop_lowest": setup.scoring_rules.drop_lowest,
        },
        "tally_dimensions": [dimension.value for dimension in setup.tally_scope.ordered()],
        "board": {
            "enabled": setup.board.enabled,
            "visibility": setup.board.visibility.value,
            "reveal": setup.board.reveal.value,
            "show_award": setup.board.show_award,
            "show_running_order": setup.board.show_running_order,
        },
        "board_slug": setup.board_slug,
        "created_at": setup.created_at,
        "updated_at": setup.updated_at,
        "version": setup.version,
    }
