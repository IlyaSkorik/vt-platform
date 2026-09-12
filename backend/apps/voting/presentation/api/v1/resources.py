"""Projecting Voting DTOs onto the wire.

One place where a view's JSON shape is decided, so the organizer's payload and the
public one cannot drift apart field by field as each view is edited.
"""

from __future__ import annotations

from typing import Any

from apps.voting.application.dto import (
    BallotDetailView,
    BallotSummaryView,
    ImportPreviewView,
    NomineeView,
    ProgramOptionView,
    PublicBallotView,
    VoteReceiptView,
)

__all__ = [
    "ballot_detail",
    "ballot_summary",
    "import_preview",
    "nominee",
    "program_option",
    "public_ballot",
    "vote_receipt",
]


def nominee(view: NomineeView) -> dict[str, Any]:
    return {
        "id": view.id,
        "position": view.position,
        "title": view.title,
        "subtitle": view.subtitle,
        "photo": view.photo,
        "number": view.number,
        "withdrawn": view.withdrawn,
        "votes": view.votes,
        "submissionId": view.submission_id,
        "programItemId": view.program_item_id,
    }


def ballot_summary(view: BallotSummaryView) -> dict[str, Any]:
    return {
        "id": view.id,
        "title": view.title,
        "slug": view.slug,
        "status": view.status,
        "competitionId": view.competition_id,
        "standalone": view.standalone,
        "nominees": view.nominees,
        "totalVotes": view.total_votes,
        "opensAt": view.opens_at,
        "closesAt": view.closes_at,
        "createdAt": view.created_at,
    }


def ballot_detail(view: BallotDetailView) -> dict[str, Any]:
    return {
        "id": view.id,
        "title": view.title,
        "description": view.description,
        "slug": view.slug,
        "status": view.status,
        "competitionId": view.competition_id,
        "standalone": view.standalone,
        "opensAt": view.opens_at,
        "closesAt": view.closes_at,
        "votesPerVoter": view.votes_per_voter,
        "cooldownHours": view.cooldown_hours,
        "reveal": view.reveal,
        "nominees": [nominee(row) for row in view.nominees],
        "totalVotes": view.total_votes,
        "voters": view.voters,
        "createdAt": view.created_at,
        "updatedAt": view.updated_at,
    }


def public_ballot(view: PublicBallotView) -> dict[str, Any]:
    return {
        "title": view.title,
        "description": view.description,
        "slug": view.slug,
        "status": view.status,
        "open": view.open,
        "votesPerVoter": view.votes_per_voter,
        "votesLeft": view.votes_left,
        "revealTotals": view.reveal_totals,
        "nominees": [
            {
                "id": row.id,
                "position": row.position,
                "title": row.title,
                "subtitle": row.subtitle,
                "photo": row.photo,
                "number": row.number,
                "votes": row.votes,
                "chosen": row.chosen,
            }
            for row in view.nominees
        ],
        "totalVotes": view.total_votes,
        "closesAt": view.closes_at,
        "closedReason": view.closed_reason,
    }


def vote_receipt(view: VoteReceiptView) -> dict[str, Any]:
    return {"ballot": public_ballot(view.ballot), "accepted": list(view.accepted)}


def import_preview(view: ImportPreviewView) -> dict[str, Any]:
    return {
        "added": [nominee(row) for row in view.added],
        # Row number and message as an object rather than a pair, because the
        # interface shows them side by side and a bare tuple invites a client to
        # guess which element is which.
        "errors": [{"row": row, "message": message} for row, message in view.errors],
        "missingColumns": list(view.missing_columns),
        "dryRun": view.dry_run,
    }


def program_option(view: ProgramOptionView) -> dict[str, Any]:
    return {"id": view.id, "name": view.name, "nominees": view.nominees}
