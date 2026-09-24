"""Translation between the panel's aggregates and their database rows.

Same contract as the setup mapper: read defensively, write exactly. A mark whose
criterion id has become unreadable is dropped rather than raised on — a sheet with one
bad entry is still a judge's opinion, and refusing to load it would lose the rest.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.judging.domain.entities import CriterionScore, JuryMember, PerformanceScoring, Scorecard
from apps.judging.domain.value_objects import JuryMemberStatus, PerformanceScoringStatus
from apps.judging.infrastructure.models import JuryMemberModel, PerformanceScoringModel, ScorecardModel

__all__ = [
    "member_to_model",
    "scorecard_to_model",
    "scoring_to_model",
    "to_member",
    "to_scorecard",
    "to_scoring",
]


def _uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Jury member
# ---------------------------------------------------------------------------


def to_member(model: JuryMemberModel) -> JuryMember:
    category_ids = [parsed for parsed in (_uuid(item) for item in (model.category_ids or [])) if parsed is not None]
    try:
        status = JuryMemberStatus(model.status)
    except ValueError:
        status = JuryMemberStatus.INVITED
    return JuryMember.rehydrate(
        member_id=model.id,
        competition_id=model.competition_id,
        full_name=model.full_name,
        email=model.email,
        created_at=model.created_at,
        updated_at=model.updated_at,
        status=status,
        user_id=model.user_id,
        title=model.title or None,
        is_chair=model.is_chair,
        category_ids=category_ids,
        sort_order=model.sort_order,
        invitation_token=model.invitation_token or None,
        invited_at=model.invited_at,
        accepted_at=model.accepted_at,
        revoked_at=model.revoked_at,
        version=model.version,
    )


def member_to_model(member: JuryMember) -> dict[str, Any]:
    return {
        "competition_id": member.competition_id,
        "full_name": member.full_name,
        "email": member.email,
        "title": member.title,
        "status": member.status.value,
        "user_id": member.user_id,
        "is_chair": member.is_chair,
        "category_ids": [str(item) for item in member.category_ids],
        "sort_order": member.sort_order,
        "invitation_token": member.invitation_token,
        "invited_at": member.invited_at,
        "accepted_at": member.accepted_at,
        "revoked_at": member.revoked_at,
        "created_at": member.created_at,
        "updated_at": member.updated_at,
        "version": member.version,
    }


# ---------------------------------------------------------------------------
# Performance scoring state
# ---------------------------------------------------------------------------


def to_scoring(model: PerformanceScoringModel) -> PerformanceScoring:
    try:
        status = PerformanceScoringStatus(model.status)
    except ValueError:
        status = PerformanceScoringStatus.PENDING
    return PerformanceScoring.rehydrate(
        scoring_id=model.id,
        competition_id=model.competition_id,
        submission_id=model.submission_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        status=status,
        opened_at=model.opened_at,
        closed_at=model.closed_at,
        version=model.version,
    )


def scoring_to_model(scoring: PerformanceScoring) -> dict[str, Any]:
    return {
        "competition_id": scoring.competition_id,
        "submission_id": scoring.submission_id,
        "status": scoring.status.value,
        "opened_at": scoring.opened_at,
        "closed_at": scoring.closed_at,
        "created_at": scoring.created_at,
        "updated_at": scoring.updated_at,
        "version": scoring.version,
    }


# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------


def to_scorecard(model: ScorecardModel) -> Scorecard:
    scores: list[CriterionScore] = []
    for entry in model.scores or []:
        if not isinstance(entry, dict):
            continue
        criterion_id = _uuid(entry.get("criterion_id"))
        if criterion_id is None:
            continue
        try:
            score = Decimal(str(entry.get("score", "0"))).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            continue
        scores.append(CriterionScore(criterion_id=criterion_id, score=score))
    return Scorecard.rehydrate(
        scorecard_id=model.id,
        competition_id=model.competition_id,
        submission_id=model.submission_id,
        jury_member_id=model.jury_member_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        scores=tuple(scores),
        comment=model.comment or None,
        submitted_at=model.submitted_at,
        version=model.version,
    )


def scorecard_to_model(card: Scorecard) -> dict[str, Any]:
    return {
        "competition_id": card.competition_id,
        "submission_id": card.submission_id,
        "jury_member_id": card.jury_member_id,
        "scores": [{"criterion_id": str(item.criterion_id), "score": str(item.score)} for item in card.scores],
        "comment": card.comment,
        "submitted_at": card.submitted_at,
        "created_at": card.created_at,
        "updated_at": card.updated_at,
        "version": card.version,
    }
