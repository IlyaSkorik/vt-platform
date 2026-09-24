"""Rendering of Judging DTOs onto their camelCase wire shapes (API-000 §7).

Kept apart from the views because three different edges render the same values — the
organizer's, the judge's and the hall's board — and a rendering that lived in one view
would be copied into the other two.

Every score is rendered as a **string**. It is a :class:`~decimal.Decimal` all the way
down for a reason, and handing it to JSON as a number would undo that at the last step.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.judging.application import dto

__all__ = [
    "board_json",
    "jury_member_json",
    "scoring_state_json",
    "setup_json",
    "tally_json",
    "task_json",
]


def _score(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _criterion_json(item: dto.CriterionView) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "maxScore": _score(item.max_score),
        "weight": _score(item.weight),
        "sortOrder": item.sort_order,
        "description": item.description,
    }


def _tier_json(item: dto.AwardTierView) -> dict[str, Any]:
    return {
        "code": item.code,
        "label": item.label,
        "minScore": _score(item.min_score),
        "maxScore": _score(item.max_score),
        "sortOrder": item.sort_order,
    }


def setup_json(view: dto.JudgingSetupView) -> dict[str, Any]:
    """The whole «Судейство» screen."""
    return {
        "competitionId": view.competition_id,
        "onlineJudging": view.online_judging,
        "awardScale": [_tier_json(item) for item in view.award_scale],
        "criteriaSets": [
            {
                "scope": item.scope,
                "targetId": item.target_id,
                "targetName": item.target_name,
                "criteria": [_criterion_json(criterion) for criterion in item.criteria],
                "maxTotal": _score(item.max_total),
            }
            for item in view.criteria_sets
        ],
        "nominations": [
            {
                "categoryId": item.category_id,
                "name": item.name,
                "disciplines": [{"id": discipline_id, "name": name} for discipline_id, name in item.disciplines],
            }
            for item in view.nominations
        ],
        "aggregation": view.aggregation,
        "dropHighest": view.drop_highest,
        "dropLowest": view.drop_lowest,
        "tallyDimensions": list(view.tally_dimensions),
        "boardEnabled": view.board_enabled,
        "boardVisibility": view.board_visibility,
        "boardReveal": view.board_reveal,
        "boardShowAward": view.board_show_award,
        "boardShowRunningOrder": view.board_show_running_order,
        "boardSlug": view.board_slug,
        "boardPath": view.board_path,
        "juryCount": view.jury_count,
        "scaleIsBanded": view.scale_is_banded,
        "updatedAt": view.updated_at,
    }


def jury_member_json(view: dto.JuryMemberView) -> dict[str, Any]:
    return {
        "id": view.id,
        "fullName": view.full_name,
        "email": view.email,
        "title": view.title,
        "status": view.status,
        "isChair": view.is_chair,
        "categoryIds": list(view.category_ids),
        "categoryNames": list(view.category_names),
        "sortOrder": view.sort_order,
        "hasAccount": view.has_account,
        "invitedAt": view.invited_at,
        "acceptedAt": view.accepted_at,
        "invitationPath": view.invitation_path,
    }


def task_json(view: dto.JuryTaskView) -> dict[str, Any]:
    """One act as its judge's tablet reads it. No participants — see ADR-0013."""
    return {
        "submissionId": view.submission_id,
        "number": view.number,
        "title": view.title,
        "categoryId": view.category_id,
        "categoryName": view.category_name,
        "disciplineName": view.discipline_name,
        "ageCategoryName": view.age_category_name,
        "participationFormatName": view.participation_format_name,
        "organization": view.organization,
        "status": view.status,
        "criteria": [_criterion_json(item) for item in view.criteria],
        "myScores": [{"criterionId": item.criterion_id, "score": _score(item.score)} for item in view.my_scores],
        "myComment": view.my_comment,
        "myTotal": _score(view.my_total),
        "submittedAt": view.submitted_at,
        "canScore": view.can_score,
        "maxTotal": _score(view.max_total),
    }


def _scorecard_json(view: dto.ScorecardView) -> dict[str, Any]:
    return {
        "juryMemberId": view.jury_member_id,
        "juryMemberName": view.jury_member_name,
        "scores": [{"criterionId": item.criterion_id, "score": _score(item.score)} for item in view.scores],
        "total": _score(view.total),
        "comment": view.comment,
        "submittedAt": view.submitted_at,
        "submitted": view.submitted,
    }


def tally_json(view: dto.TallySheetView) -> dict[str, Any]:
    return {
        "competitionId": view.competition_id,
        "groups": [
            {
                "key": group.key,
                "heading": group.heading,
                "categoryId": group.category_id,
                "tallies": [
                    {
                        "submissionId": item.submission_id,
                        "number": item.number,
                        "title": item.title,
                        "organization": item.organization,
                        "score": _score(item.score),
                        "maxScore": _score(item.max_score),
                        "awardCode": item.award_code,
                        "awardLabel": item.award_label,
                        "submittedCount": item.submitted_count,
                        "expectedJudges": item.expected_judges,
                        "status": item.status,
                        "scorecards": [_scorecard_json(card) for card in item.scorecards],
                    }
                    for item in group.tallies
                ],
            }
            for group in view.groups
        ],
        "aggregation": view.aggregation,
        "scaleIsBanded": view.scale_is_banded,
        "unawardedCount": view.unawarded_count,
    }


def scoring_state_json(view: dto.ScoringStateView) -> dict[str, Any]:
    return {
        "submissionId": view.submission_id,
        "status": view.status,
        "openedAt": view.opened_at,
        "closedAt": view.closed_at,
    }


def _board_entry_json(view: dto.BoardEntryView) -> dict[str, Any]:
    return {
        "number": view.number,
        "title": view.title,
        "organization": view.organization,
        "categoryName": view.category_name,
        "ageCategoryName": view.age_category_name,
        "status": view.status,
        "score": _score(view.score),
        "maxScore": _score(view.max_score),
        "awardLabel": view.award_label,
        "submittedCount": view.submitted_count,
        "expectedJudges": view.expected_judges,
        "judges": [{"name": judge.name, "total": _score(judge.total)} for judge in view.judges],
    }


def board_json(view: dto.BoardView) -> dict[str, Any]:
    """The hall's screen, already filtered to what the organizer allowed."""
    return {
        "competitionTitle": view.competition_title,
        "visibility": view.visibility,
        "reveal": view.reveal,
        "showAward": view.show_award,
        "current": _board_entry_json(view.current) if view.current is not None else None,
        "recent": [_board_entry_json(item) for item in view.recent],
    }
