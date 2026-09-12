"""Persistence for the :class:`Ballot` aggregate: the root and its nominees.

Two tables rather than one JSON document, because a nominee is what the organizer
manipulates one at a time and what a vote points at: it has its own identity, its
own ordinal and its own running count, and that count is a column the database
must be able to increment atomically.

``organization_id`` is required and ``competition_id`` is nullable, and that pair
is the whole feature: a ballot belongs to whoever runs it, and it may or may not
belong to a festival that lives on this platform. Cross-context references
(``competition_id``, ``submission_id``, ``program_item_id``) are id-only
``UUIDField`` columns and never foreign keys (ARCH-001 §9.2) — a ballot is the
record of what the audience was asked and must survive a submission being
reworked, a programme being deleted, or a festival being renamed.
"""

from __future__ import annotations

from django.db import models

from apps.voting.domain.value_objects import BallotStatus, RevealPolicy

from .base import BasePersistenceModel

__all__ = [
    "BallotModel",
    "BallotNomineeModel",
    "BallotStatusChoices",
    "RevealPolicyChoices",
]


class BallotStatusChoices(models.TextChoices):
    """Ballot lifecycle states (mirrors the domain ``BallotStatus``)."""

    DRAFT = BallotStatus.DRAFT.value, "Черновик"
    OPEN = BallotStatus.OPEN.value, "Идёт голосование"
    CLOSED = BallotStatus.CLOSED.value, "Завершено"


class RevealPolicyChoices(models.TextChoices):
    """Who may see the running count (mirrors the domain ``RevealPolicy``)."""

    ALWAYS = RevealPolicy.ALWAYS.value, "Всегда"
    AFTER_CLOSE = RevealPolicy.AFTER_CLOSE.value, "После завершения"
    NEVER = RevealPolicy.NEVER.value, "Только организатору"


class BallotModel(BasePersistenceModel):
    """Database row for a ballot (persistence only — no business logic)."""

    organization_id = models.UUIDField()
    # Null means the ballot stands on its own: a festival that has not moved onto
    # the platform but still wants an audience vote. The case this context exists for.
    competition_id = models.UUIDField(null=True, blank=True, default=None)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    # The only credential the public page has. Unique platform-wide and permanent.
    slug = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=BallotStatusChoices.choices, default=BallotStatusChoices.DRAFT)

    # The voting window. Both ends optional — an organizer may drive it by hand.
    opens_at = models.DateTimeField(null=True, blank=True, default=None)
    closes_at = models.DateTimeField(null=True, blank=True, default=None)

    # The rules.
    votes_per_voter = models.PositiveSmallIntegerField(default=1)
    # Hours before a voter's votes are replenished; 0 means once, for the whole ballot.
    cooldown_hours = models.PositiveIntegerField(default=0)
    reveal = models.CharField(max_length=16, choices=RevealPolicyChoices.choices, default=RevealPolicyChoices.AFTER_CLOSE)

    # When the vote actually started and stopped, as opposed to when it was scheduled to.
    opened_at = models.DateTimeField(null=True, blank=True, default=None)
    closed_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "voting_ballot"
        verbose_name = "ballot"
        verbose_name_plural = "ballots"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["competition_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=BallotStatusChoices.values),
                name="voting_ballot_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(reveal__in=RevealPolicyChoices.values),
                name="voting_ballot_reveal_valid",
            ),
            # Unconditional: a revoked link must never be handed out again, so the
            # slug stays claimed even after a soft delete (as in Programs).
            models.UniqueConstraint(fields=["slug"], name="voting_ballot_slug_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.title} (/{self.slug})"


class BallotNomineeModel(BasePersistenceModel):
    """Database row for one nominee (persistence only).

    Holds the nominee's *own* display data rather than a reference to somebody
    else's. That is what lets one ballot be seeded from a programme and the next
    one typed in by hand, with everything downstream unable to tell the difference
    — and what keeps a finished vote readable after the programme it came from is
    gone.
    """

    ballot = models.ForeignKey("voting.BallotModel", on_delete=models.CASCADE, related_name="nominees")
    # Where the nominee sits on the page (1..N, rewritten from the aggregate on save).
    position = models.PositiveIntegerField(default=0)
    # The number the act was announced under, when it has one: the audience looks
    # for the number the host just read out, not for a name they may not have caught.
    number = models.PositiveIntegerField(null=True, blank=True, default=None)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=200, blank=True, default="")
    photo = models.CharField(max_length=1024, null=True, blank=True, default=None)
    # Off the ballot but still in the results, with the votes they had. Deleting the
    # row instead would quietly change a total people have already seen.
    withdrawn = models.BooleanField(default=False)
    # Denormalized count, advanced in the same transaction as the vote insert. The
    # votes table stays the record of truth and the count can be rebuilt from it.
    votes = models.PositiveIntegerField(default=0)
    # Optional id-only links back to where this nominee came from.
    submission_id = models.UUIDField(null=True, blank=True, default=None)
    program_item_id = models.UUIDField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "voting_ballot_nominee"
        verbose_name = "nominee"
        verbose_name_plural = "nominees"
        ordering = ["position"]
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["ballot", "position"]),
        ]

    def __str__(self) -> str:
        return f"{self.position}. {self.title}"
