"""The ``Vote`` — one person, one nominee, one moment.

Deliberately outside the :class:`~apps.voting.domain.entities.Ballot` aggregate.
A ballot has tens of nominees and tens of thousands of votes; making the votes
children of the aggregate would mean loading a hall's worth of rows to accept one
more. They are their own thing, append-only, with their own repository.

A vote is never edited and never soft-deleted. It happened.

**Who cast it** is an opaque pair of strings here. The domain knows that a vote
carries a ``voter_key`` (which voter) and a ``network_key`` (roughly, from where),
and that two votes with the same keys in the same window are the same person
voting twice. It does *not* know that those are salted hashes of a cookie and an
address prefix — that is a privacy decision made in infrastructure, where the
pepper lives, and the domain is better off unable to reverse them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from .exceptions import InvalidBallotDataError

__all__ = ["NetworkKey", "Vote", "VoterKey"]


@dataclass(frozen=True, slots=True)
class VoterKey:
    """Which voter, as an opaque token that cannot be turned back into a person.

    Scoped to one ballot by construction (infrastructure mixes the ballot id into
    it), so the same visitor voting in two ballots produces two unrelated keys and
    a dump of this table cannot be used to follow anybody around.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 128:
            raise InvalidBallotDataError("Некорректный идентификатор голосующего.")


@dataclass(frozen=True, slots=True)
class NetworkKey:
    """Roughly where the vote came from, as an opaque token.

    Not an address: a coarse prefix, salted and hashed. Enough to notice that four
    thousand votes arrived from one place, useless for locating anybody — which is
    exactly as much as a soft brake needs (LEGAL-001).
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 128:
            raise InvalidBallotDataError("Некорректный идентификатор сети.")


@dataclass(frozen=True, slots=True)
class Vote:
    """One cast vote, as it is written down and never changed again."""

    id: uuid.UUID
    ballot_id: uuid.UUID
    nominee_id: uuid.UUID
    voter: VoterKey
    network: NetworkKey
    #: Which repeat window this vote belongs to — always ``0`` for a one-shot
    #: ballot. Part of the uniqueness rule, so "one vote per person per period"
    #: is enforced by an index rather than by a query that can race.
    bucket: int
    cast_at: datetime

    def __post_init__(self) -> None:
        if self.bucket < 0:
            raise InvalidBallotDataError("Некорректное окно голосования.")
