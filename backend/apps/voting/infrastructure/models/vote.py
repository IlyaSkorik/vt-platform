"""Persistence for one cast vote.

The only table in this codebase that does **not** inherit
:class:`~apps.voting.infrastructure.models.base.BasePersistenceModel`, and
deliberately: a vote is never edited, so it has no ``updated_at`` and no
``version``; and it is never soft-deleted, because a vote that happened happened.
Carrying those four columns on the largest table here would be four lies and a
measurable amount of disk.

**The uniqueness rule is the anti-fraud mechanism.** "One vote per person per
nominee per period" is a unique index over
``(ballot, voter_key, bucket, nominee)``, not a check-then-insert — the check
version races against itself the moment two requests arrive together, which on a
ballot being voted by a hall is constantly. A duplicate is a database refusal that
the use case turns into a friendly "вы уже голосовали".

**Nothing here identifies a person.** ``voter_key`` is a salted hash of a cookie
the server issued, mixed with the ballot's id so the same visitor in two ballots
produces two unrelated keys. ``network_key`` is a salted hash of a coarse address
prefix — enough to notice a flood, useless for finding anybody (LEGAL-001). No raw
address is stored anywhere.
"""

from __future__ import annotations

import os
import time
import uuid

from django.db import models
from django.utils import timezone

__all__ = ["VoteModel"]

_UUID_V7_VERSION = 7


def uuid7() -> uuid.UUID:
    """Generate a time-ordered UUID version 7 (RFC 9562 §5.7).

    Time-ordered matters more here than anywhere else in this context: votes are
    inserted in a burst and a random primary key would scatter them across the
    index, turning an append into a page-fault storm.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = (rand >> 68) & 0x0FFF
    rand_b = rand & ((1 << 62) - 1)
    value = (unix_ms & ((1 << 48) - 1)) << 80 | _UUID_V7_VERSION << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)


class VoteModel(models.Model):
    """Database row for one cast vote (persistence only — append-only)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    # Id-only, like every other cross-row reference in this context: the count on
    # the nominee is what the page reads, and this table is the record behind it.
    ballot_id = models.UUIDField()
    nominee_id = models.UUIDField()
    voter_key = models.CharField(max_length=128)
    network_key = models.CharField(max_length=128)
    # Which repeat window this vote falls in; always 0 for a one-shot ballot, so the
    # same index serves both kinds without a special case.
    bucket = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "voting_vote"
        verbose_name = "vote"
        verbose_name_plural = "votes"
        indexes = [
            # "How many votes has this person spent in this window?" — the limit check.
            models.Index(fields=["ballot_id", "voter_key", "bucket"]),
            # "How much has this network sent in this window?" — the soft brake.
            models.Index(fields=["ballot_id", "network_key", "bucket"]),
            # Rebuilding a nominee's count from the record of truth.
            models.Index(fields=["nominee_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["ballot_id", "voter_key", "bucket", "nominee_id"],
                name="voting_vote_one_per_voter_per_window",
            ),
            models.CheckConstraint(condition=models.Q(bucket__gte=0), name="voting_vote_bucket_non_negative"),
        ]

    def __str__(self) -> str:
        return f"vote for {self.nominee_id} at {self.created_at:%Y-%m-%d %H:%M}"
