"""``DjangoVoteRepository`` — ORM adapter for cast votes.

Append-only. The interesting method is :meth:`cast`, which does the one thing this
whole context has to get right: write a vote and advance the nominee's count in a
single transaction, and let the database — not a preceding ``SELECT`` — decide
whether this person has already voted.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Count, F

from apps.voting.domain.exceptions import AlreadyVotedError
from apps.voting.domain.vote import NetworkKey, VoterKey
from apps.voting.infrastructure.models import BallotNomineeModel, VoteModel

from .exceptions import PersistenceError

__all__ = ["DjangoVoteRepository"]


class DjangoVoteRepository:
    """Django ORM adapter implementing the ``VoteRepository`` port."""

    def cast(
        self,
        *,
        vote_id: uuid.UUID,
        ballot_id: uuid.UUID,
        nominee_id: uuid.UUID,
        voter: VoterKey,
        network: NetworkKey,
        bucket: int,
        now: datetime,
    ) -> None:
        """Record one vote and advance the nominee's count, atomically.

        The duplicate check is the unique index, not a query. A check-then-insert
        races against itself the moment two requests arrive together — which, on a
        ballot being voted by a hall at the end of a number, is continuously — and
        the race lets the same person through twice. Here the second insert is
        refused by the database and becomes :class:`AlreadyVotedError`.

        The count is advanced with ``F()``, so it is the database that adds one to
        whatever is there rather than this process writing back a number it read a
        moment ago. Two simultaneous votes therefore produce two, not one.
        """
        try:
            with transaction.atomic():
                VoteModel.objects.create(
                    id=vote_id,
                    ballot_id=ballot_id,
                    nominee_id=nominee_id,
                    voter_key=voter.value,
                    network_key=network.value,
                    bucket=bucket,
                    created_at=now,
                )
                BallotNomineeModel.objects.filter(pk=nominee_id).update(votes=F("votes") + 1, updated_at=now)
        except IntegrityError as exc:
            raise AlreadyVotedError("Вы уже голосовали за этого участника.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to record the vote.") from exc

    def spent_by_voter(self, *, ballot_id: uuid.UUID, voter: VoterKey, bucket: int) -> int:
        """How many votes this person has already used in this window."""
        try:
            return VoteModel.objects.filter(ballot_id=ballot_id, voter_key=voter.value, bucket=bucket).count()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to count the voter's votes.") from exc

    def chosen_by_voter(self, *, ballot_id: uuid.UUID, voter: VoterKey, bucket: int) -> set[uuid.UUID]:
        """Which nominees this person has already backed in this window.

        The voting page reads this to show someone what they picked rather than an
        empty form they will try to fill in again.
        """
        try:
            return set(VoteModel.objects.filter(ballot_id=ballot_id, voter_key=voter.value, bucket=bucket).values_list("nominee_id", flat=True))
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to read the voter's choices.") from exc

    def sent_by_network(self, *, ballot_id: uuid.UUID, network: NetworkKey, bucket: int) -> int:
        """How many votes have come from this network in this window."""
        try:
            return VoteModel.objects.filter(ballot_id=ballot_id, network_key=network.value, bucket=bucket).count()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to count the network's votes.") from exc

    def tally(self, ballot_id: uuid.UUID) -> dict[uuid.UUID, int]:
        """Recount from the record of truth, for repairing a drifted counter."""
        try:
            rows = VoteModel.objects.filter(ballot_id=ballot_id).values_list("nominee_id").annotate(total=Count("id"))
            return dict(rows)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to tally the votes.") from exc

    def voters(self, ballot_id: uuid.UUID) -> int:
        """How many distinct people have voted — the turnout, not the vote count."""
        try:
            return VoteModel.objects.filter(ballot_id=ballot_id).values("voter_key").distinct().count()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to count voters.") from exc
