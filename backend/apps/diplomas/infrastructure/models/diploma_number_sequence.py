"""``DiplomaNumberSequenceModel`` — the counter behind a diploma number.

A dedicated, monotonically increasing counter row replaces the old
``max(number) + 1`` scan: reserving a value is a single ``SELECT … FOR UPDATE``
plus an increment inside one transaction, so any number of parallel Celery
workers can generate diplomas at once and never collide. Nothing derives a number
from the diplomas table any more.

One row per :attr:`scope` — the competition year, which is part of the number
(``VT-2026-000001``), so each year runs its own ``000001…`` series while the
number as a whole stays unique. The unique constraint on ``scope`` is what makes
the get-or-create race safe.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["DiplomaNumberSequenceModel"]


class DiplomaNumberSequenceModel(BasePersistenceModel):
    """Database row for one number series (persistence only - no business logic)."""

    #: The series key. Currently the competition year ("2026"); kept a string so a
    #: future format can scope numbers differently without a migration.
    scope = models.CharField(max_length=32)

    #: Last value handed out. The next reservation returns ``current_number + 1``.
    current_number = models.PositiveBigIntegerField(default=0)

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_diploma_number_sequence"
        verbose_name = "diploma number sequence"
        verbose_name_plural = "diploma number sequences"
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(fields=["scope"], name="diplomas_number_sequence_scope_unique"),
        ]

    def __str__(self) -> str:
        return f"Diploma numbers {self.scope}: {self.current_number}"
