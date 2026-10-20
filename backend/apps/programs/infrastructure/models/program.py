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

__all__ = [
    "ProgramColumnModel",
    "ProgramItemKindChoices",
    "ProgramItemModel",
    "ProgramItemProgressChoices",
    "ProgramModel",
    "ProgramShareModel",
]


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
    # How many slot numbers this programme has issued since freezing. Monotonic, so a
    # removed slot's number is retired rather than handed to the next act.
    numbers_issued = models.PositiveIntegerField(default=0)
    # When the numbers stopped following the running order - the first publication. Null
    # while the programme is still being assembled.
    numbers_frozen_at = models.DateTimeField(null=True, blank=True, default=None)
    # The rules the running order was last generated from, so "пересобрать" needs no
    # form. One JSON column rather than a dozen scalar ones: nothing queries or joins on
    # a generation setting, and the set of knobs is expected to grow. An empty object
    # means "this programme was only ever built by hand".
    arrangement = models.JSONField(default=dict, blank=True)
    # When a rebuild last replaced the whole running order. The rows it replaced carry
    # this same instant as their ``deleted_at``, which is what makes one timestamp
    # enough to find the state again - see ``Program.restore_order``. Null once the
    # undo has used it up, or when no rebuild has happened.
    rebuilt_at = models.DateTimeField(null=True, blank=True, default=None, editable=False)

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


class ProgramItemProgressChoices(models.TextChoices):
    """How far a slot has got on the day (mirrors the domain ``ProgramItemProgress``)."""

    PENDING = "PENDING", "Pending"
    ON_STAGE = "ON_STAGE", "On stage"
    PERFORMED = "PERFORMED", "Performed"
    SKIPPED = "SKIPPED", "Skipped"


class ProgramColumnModel(BasePersistenceModel):
    """A column the organizer added to one programme and fills in by hand.

    A table rather than JSON on the programme row, because items reference these by id:
    a column's identity is what its values hang off, so it gets a row of its own.
    """

    program = models.ForeignKey(
        "programs.ProgramModel",
        on_delete=models.CASCADE,
        related_name="custom_columns",
    )
    position = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=120)

    class Meta(BasePersistenceModel.Meta):
        db_table = "programs_program_column"
        verbose_name = "programme column"
        verbose_name_plural = "programme columns"
        ordering = ["position"]
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["program", "position"]),
        ]

    def __str__(self) -> str:
        return self.title


class ProgramItemModel(BasePersistenceModel):
    """Database row for one slot of a program (persistence only)."""

    program = models.ForeignKey(
        "programs.ProgramModel",
        on_delete=models.CASCADE,
        related_name="items",
    )
    # Where the row sits in the running order (1..N, rewritten on every save).
    position = models.PositiveIntegerField(default=0)
    # The participant's permanent number. Assigned once and never rewritten by a
    # reorder, so a rearranged programme can read 2, 3, 5, 4 - see ``ProgramItem``.
    number = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=24, choices=ProgramItemKindChoices.choices)
    # Set for standalone blocks ("Обед"); blank for a performance, whose name is read
    # from the act so a corrected name shows up everywhere at once.
    title = models.CharField(max_length=200, blank=True, default="")
    duration_seconds = models.PositiveIntegerField()
    # Id-only reference into the Applications context; set only for performances.
    submission_id = models.UUIDField(null=True, blank=True, default=None)
    # Hand-filled values keyed by custom column id. One JSON document because they are
    # read and written with the row and never queried field by field.
    custom_values = models.JSONField(default=dict, blank=True)
    # How far this slot has got on the day itself; the host drives it from their link.
    progress = models.CharField(
        max_length=16,
        choices=ProgramItemProgressChoices.choices,
        default=ProgramItemProgressChoices.PENDING,
    )

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
            models.CheckConstraint(
                condition=models.Q(progress__in=ProgramItemProgressChoices.values),
                name="programs_item_progress_valid",
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
    with an HTTP view.

    ``columns`` is what the edition *is*: the columns of the programme table its reader
    sees. ``item_ids`` optionally narrows the rows - an empty list means "every row",
    which keeps a screen by the stage correct as the programme grows. Both are stored as
    JSON: they are selections over the programme, read as one value and never queried
    field by field. The slug is unique platform-wide and permanent: it is the only
    credential a public link has.
    """

    program = models.ForeignKey(
        "programs.ProgramModel",
        on_delete=models.CASCADE,
        related_name="shares",
    )
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=64)
    columns = models.JSONField(default=list, blank=True)
    item_ids = models.JSONField(default=list, blank=True)
    # Whether whoever holds this link may drive the running order on the day - the host's
    # edition. Every other link is read-only.
    controls_running_order = models.BooleanField(default=False)

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
