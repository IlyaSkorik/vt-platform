"""``BallotMapper`` — ACL between the ``Ballot`` aggregate and its rows.

The single component permitted to know both the framework-free aggregate and its
Django models. Translates in both directions and does nothing else: no validation,
no workflow, no ``save()``. Timestamps are copied verbatim — the aggregate owns
those instants.
"""

from __future__ import annotations

from collections.abc import Iterable

from apps.voting.domain.entities import Ballot, BallotNominee
from apps.voting.domain.value_objects import (
    BallotStatus,
    BallotTitle,
    Cooldown,
    NomineeText,
    PublicSlug,
    RevealPolicy,
    VoteLimit,
    VotingWindow,
)
from apps.voting.infrastructure.models import BallotModel, BallotNomineeModel

__all__ = ["BallotMapper"]


class BallotMapper:
    """Bidirectional translator between ``Ballot`` and its models."""

    @staticmethod
    def to_domain(model: BallotModel, nominees: Iterable[BallotNomineeModel]) -> Ballot:
        """Reconstruct the aggregate from its rows (no re-validation, no events)."""
        return Ballot.rehydrate(
            ballot_id=model.id,
            organization_id=model.organization_id,
            title=BallotTitle(model.title),
            slug=PublicSlug(model.slug),
            status=BallotStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            competition_id=model.competition_id,
            description=model.description,
            window=VotingWindow(opens_at=model.opens_at, closes_at=model.closes_at),
            vote_limit=VoteLimit(model.votes_per_voter),
            cooldown=Cooldown(model.cooldown_hours),
            reveal=RevealPolicy(model.reveal),
            nominees=[BallotMapper.nominee_to_domain(row) for row in nominees],
            opened_at=model.opened_at,
            closed_at=model.closed_at,
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def nominee_to_domain(row: BallotNomineeModel) -> BallotNominee:
        """Reconstruct one nominee from its row."""
        return BallotNominee(
            _id=row.id,
            _title=NomineeText(row.title),
            _subtitle=NomineeText(row.subtitle),
            _photo=row.photo,
            _number=row.number,
            _position=row.position,
            _withdrawn=row.withdrawn,
            _votes=row.votes,
            _submission_id=row.submission_id,
            _program_item_id=row.program_item_id,
        )

    @staticmethod
    def root_columns(ballot: Ballot) -> dict[str, object]:
        """Flatten the aggregate root into ``BallotModel`` column values."""
        return {
            "id": ballot.id,
            "organization_id": ballot.organization_id,
            "competition_id": ballot.competition_id,
            "title": ballot.title.value,
            "description": ballot.description,
            "slug": ballot.slug.value,
            "status": ballot.status.value,
            "opens_at": ballot.window.opens_at,
            "closes_at": ballot.window.closes_at,
            "votes_per_voter": ballot.vote_limit.value,
            "cooldown_hours": ballot.cooldown.hours,
            "reveal": ballot.reveal.value,
            "opened_at": ballot.opened_at,
            "closed_at": ballot.closed_at,
            "created_at": ballot.created_at,
            "updated_at": ballot.updated_at,
            "deleted_at": ballot.deleted_at,
            "version": ballot.version,
        }

    @staticmethod
    def nominee_columns(nominee: BallotNominee, *, ballot_id: object, now: object) -> dict[str, object]:
        """Flatten one nominee into ``BallotNomineeModel`` column values."""
        return {
            "id": nominee.id,
            "ballot_id": ballot_id,
            "position": nominee.position,
            "number": nominee.number,
            "title": nominee.title.value,
            "subtitle": nominee.subtitle.value,
            "photo": nominee.photo,
            "withdrawn": nominee.withdrawn,
            "votes": nominee.votes,
            "submission_id": nominee.submission_id,
            "program_item_id": nominee.program_item_id,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
            "version": 1,
        }
