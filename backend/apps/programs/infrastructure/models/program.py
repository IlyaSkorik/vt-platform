"""Persistence for the :class:`Program` aggregate: the root and its two child tables.

Three tables, not one JSON document, because a program is the thing the organizer
manipulates item by item and publishes subsets of - so its items are rows with their
own identity and their own ordinal, and a public link is a row with a unique slug the
database itself can guarantee.

Order lives in :attr:`ProgramItemModel.position`, which the repository rewrites from
the aggregate's list on every save: the aggregate owns the sequence, the column only
records it. Cross-context references (``competition_id``, ``nomination_id``,
``submission_id``) are id-only ``UUIDField`` columns and never foreign keys
(ARCH-001 §9.2) - a program must survive a submission being reworked in another
context, and it holds no lock on it.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["ProgramItemKindChoices", "ProgramItemModel", "ProgramModel", "ProgramShareModel"]


class ProgramItemKindChoices(models.TextChoices):
    """What a slot is (mirrors the domain ``ProgramItemKind``).

    The kinds beyond ``PERFORMANCE`` and ``BREAK`` are already valid here: a new kind
    of service block is a value, not a schema change, which is the whole point of one
    ``ProgramItem`` table with a ``kind`` column.
    """

    PERFORMANCE = "PERFORMANCE", "Performance"
    BREAK = "BREAK", "Break"
    OPENING = "OPENING", "Opening"
    AWARD = "AWARD", "Award ceremony"
    MASTER_CLASS = "MASTER_CLASS", "Master class"
    TECHNICAL = "TECHNICAL", "Technical block"


class ProgramModel(BasePersistenceModel):
    """Database row for a program (persistence only - no business logic)."""

    competition_id = models.UUIDField()
    # Null means the program spans the whole competition rather than one nomination.
    nomination_id = models.UUIDField(null=True, blank=True, default=None)
    name = models.CharField(max_length=200)
    # The wall-clock start of the first item; null while the day is not timed yet.
    starts_at = models.DateTimeField(null=True, blank=True, default=None)
    # Padding added to every performance slot when the schedule is computed. Never
    # changes an act's own duration.
    buffer_seconds = models.PositiveIntegerField(default=0)

    class Meta(BasePersistenceModel.Meta):
        db_table = "programs_program"
        verbose_name = "program"
        verbose_name_plural = "programs"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
            models.Index(fields=["nomination_id"]),
        ]

    def __str__(self) -> str:
        return self.name


class ProgramItemModel(BasePersistenceModel):
    """Database row for one slot of a program (persistence only)."""

    program = models.ForeignKey(
        "programs.ProgramModel",
        on_delete=models.CASCADE,
        related_name="items",
    )
    position = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=24, choices=ProgramItemKindChoices.choices)
    # Set for standalone blocks ("Обед"); blank for a performance, whose name is read
    # from the act so a corrected name shows up everywhere at once.
    title = models.CharField(max_length=200, blank=True, default="")
    duration_seconds = models.PositiveIntegerField()
    # Id-only reference into the Applications context; set only for performances.
    submission_id = models.UUIDField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "programs_program_item"
        verbose_name = "program item"
        verbose_name_plural = "program items"
        ordering = ["position"]
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["program", "position"]),
            models.Index(fields=["submission_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(kind__in=ProgramItemKindChoices.values),
                name="programs_item_kind_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(duration_seconds__gt=0),
                name="programs_item_duration_positive",
            ),
            # One act, one slot: a second slot for the same submission would double it
            # in the running order and in every schedule computed from it.
            models.UniqueConstraint(
                fields=["program", "submission_id"],
                condition=models.Q(deleted_at__isnull=True, submission_id__isnull=False),
                name="programs_item_unique_performance_per_program",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.position}. {self.title or self.kind}"


class ProgramShareModel(BasePersistenceModel):
    """Database row for a public edition of a program (the task's ``ProgramView``).

    Named ``share`` rather than ``view`` so nothing in a Django codebase confuses it
    with an HTTP view. ``item_ids`` is a *selection over* the program - an empty list
    means "the whole program", which keeps a screen by the stage correct as the
    program grows. The slug is unique platform-wide and permanent: it is the only
    credential a public link has.
    """

    program = models.ForeignKey(
        "programs.ProgramModel",
        on_delete=models.CASCADE,
        related_name="shares",
    )
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=64)
    item_ids = models.JSONField(default=list, blank=True)

    class Meta(BasePersistenceModel.Meta):
        db_table = "programs_program_share"
        verbose_name = "public program"
        verbose_name_plural = "public programs"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["program"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            # Unconditional: a revoked link must never be handed out again, so the
            # slug stays claimed even after a soft delete.
            models.UniqueConstraint(fields=["slug"], name="programs_share_slug_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.name} (/{self.slug})"
