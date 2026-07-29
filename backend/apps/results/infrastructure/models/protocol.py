"""Persistence for the :class:`Protocol` aggregate: the root and its rows.

Two tables, not one JSON document, because a row is what the jury manipulates one at a
time and what a result hangs off: it has its own identity, its own ordinal and its own
award, and the award column is the thing an organizer will eventually want to filter and
count by. Contrast the Applications context, which keeps a submission's children as JSON
precisely because nothing queries them independently.

Order lives in :attr:`ProtocolRowModel.position`, which the repository rewrites from the
aggregate's list on every save: the aggregate owns the sequence, the column only records
it. Cross-context references (``competition_id``, ``nomination_id``, ``submission_id``,
``seeded_from_program_id``) are id-only ``UUIDField`` columns and never foreign keys
(ARCH-001 §9.2) - a protocol is the record of what happened and must survive a submission
being reworked, a programme being deleted, or a nomination being renamed in another
context.
"""

from __future__ import annotations

from django.db import models

from apps.results.domain.value_objects import AwardKind, ProtocolStatus

from .base import BasePersistenceModel

__all__ = ["AwardChoices", "ProtocolModel", "ProtocolRowModel", "ProtocolStatusChoices"]


class ProtocolStatusChoices(models.TextChoices):
    """Whether the results are public (mirrors the domain ``ProtocolStatus``)."""

    DRAFT = ProtocolStatus.DRAFT.value, "Draft"
    PUBLISHED = ProtocolStatus.PUBLISHED.value, "Published"


class AwardChoices(models.TextChoices):
    """The award vocabulary (mirrors the domain ``AwardKind``).

    Derived from the enum rather than retyped, so a new award is a value in one place.
    The database still constrains the column to these names, which is what keeps a
    hand-written UPDATE from inventing a tenth kind of diploma.
    """

    GRAND_PRIX = AwardKind.GRAND_PRIX.value, "Гран-при"
    GRAND_PRIX_NOMINEE = AwardKind.GRAND_PRIX_NOMINEE.value, "Номинант на Гран-при"
    LAUREATE_I = AwardKind.LAUREATE_I.value, "Лауреат I степени"
    LAUREATE_II = AwardKind.LAUREATE_II.value, "Лауреат II степени"
    LAUREATE_III = AwardKind.LAUREATE_III.value, "Лауреат III степени"
    DIPLOMANT_I = AwardKind.DIPLOMANT_I.value, "Дипломант I степени"
    DIPLOMANT_II = AwardKind.DIPLOMANT_II.value, "Дипломант II степени"
    DIPLOMANT_III = AwardKind.DIPLOMANT_III.value, "Дипломант III степени"
    PARTICIPANT = AwardKind.PARTICIPANT.value, "Диплом участника"


class ProtocolModel(BasePersistenceModel):
    """Database row for one nomination's protocol (persistence only - no logic)."""

    competition_id = models.UUIDField()
    nomination_id = models.UUIDField()
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=16,
        choices=ProtocolStatusChoices.choices,
        default=ProtocolStatusChoices.DRAFT,
    )
    # Which columns the public page shows. JSON because it is a selection read and written
    # as one value, never queried column by column. Empty means the safe default set.
    public_columns = models.JSONField(default=list, blank=True)
    # Minted at the first publication and permanent from then on; blank until then.
    slug = models.CharField(max_length=64, blank=True, default="")
    # How many times these results have been published (0 = never).
    revision = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True, default=None)
    # The aggregate version the current revision was published at. What
    # ``has_unpublished_changes`` compares against, so "изменено после публикации" is
    # derived rather than a flag some edit path could forget to set.
    published_version = models.PositiveIntegerField(default=0)
    # The revision that is currently public: the heading, the columns and the verdict itself,
    # frozen at publication. One JSON document because it is read and written whole and never
    # queried field by field - and because it is a *snapshot*, so normalizing it into rows
    # would invite somebody to join it against the live ones. Empty until first published.
    published_snapshot = models.JSONField(null=True, blank=True, default=None)
    # The programme whose running order seeded this protocol, for the record.
    seeded_from_program_id = models.UUIDField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "results_protocol"
        verbose_name = "protocol"
        verbose_name_plural = "protocols"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
            models.Index(fields=["competition_id", "status"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=ProtocolStatusChoices.values),
                name="results_protocol_status_valid",
            ),
            # One nomination, one protocol. Two would each be a partial account of the
            # same results and nothing downstream could say which a diploma came from.
            models.UniqueConstraint(
                fields=["competition_id", "nomination_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="results_protocol_unique_per_nomination",
            ),
            # Unconditional on purpose: a slug that has ever been published must never be
            # handed to a different protocol, including after this one is deleted. The
            # blank default is excluded so unpublished drafts do not collide with
            # each other.
            models.UniqueConstraint(
                fields=["slug"],
                condition=~models.Q(slug=""),
                name="results_protocol_slug_unique",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ProtocolRowModel(BasePersistenceModel):
    """Database row for one act's line in a protocol (persistence only).

    ``award`` is nullable and stays nullable: a blank result is a legitimate, permanent
    state (an act that did not appear), not a step towards a filled one.
    """

    protocol = models.ForeignKey(
        "results.ProtocolModel",
        on_delete=models.CASCADE,
        related_name="rows",
    )
    # Where the line sits in the protocol (1..N, rewritten from the aggregate on save).
    position = models.PositiveIntegerField(default=0)
    # The number the act performed under - the programme's, when seeded from one. Travels
    # with the row through a reorder, so a protocol legitimately reads 1, 2, 4, 3.
    number = models.PositiveIntegerField(default=0)
    # Id-only reference into the Applications context.
    submission_id = models.UUIDField()
    award = models.CharField(max_length=24, choices=AwardChoices.choices, null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "results_protocol_row"
        verbose_name = "protocol row"
        verbose_name_plural = "protocol rows"
        ordering = ["position"]
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["protocol", "position"]),
            models.Index(fields=["submission_id"]),
            # Answers "what did this competition award, and how much of it" without
            # scanning: the reporting question the award column exists for.
            models.Index(fields=["protocol", "award"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(award__isnull=True) | models.Q(award__in=AwardChoices.values),
                name="results_row_award_valid",
            ),
            # One act, one result. A second row for the same submission would let two
            # awards be entered for it and only one of them reach the diploma.
            models.UniqueConstraint(
                fields=["protocol", "submission_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="results_row_unique_submission_per_protocol",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number}. {self.award or '—'}"
