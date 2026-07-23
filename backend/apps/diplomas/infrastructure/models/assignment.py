"""``AssignmentModel`` - binds a template to a (competition, nomination) pair.

Persistence model only (no business logic). This is the sole place a template
becomes tied to a competition: the constructor and the template library know
nothing about nominations.

Cross-context references are id-only (ARCH-001 §7.2): ``competition_id`` and
``category_id`` (the nomination) point at rows owned by the Competitions context
and are therefore plain ``UUIDField`` columns, **not** Django FKs. The link to the
template lives inside this context, so it is a real FK (``PROTECT`` — a template
in use cannot be deleted out from under its assignments).
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["AssignmentModel"]


class AssignmentModel(BasePersistenceModel):
    """Database row for a template assignment (persistence only - no business logic)."""

    competition_id = models.UUIDField()
    # The nomination the assignment applies to. Nomination == Category in the
    # Competitions context (see apps.competitions ... CategoryModel).
    category_id = models.UUIDField()
    template = models.ForeignKey(
        "diplomas.TemplateModel",
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_assignment"
        verbose_name = "template assignment"
        verbose_name_plural = "template assignments"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
            models.Index(fields=["template"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["competition_id", "category_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="diplomas_unique_assignment",
            ),
        ]

    def __str__(self) -> str:
        return f"Assignment {self.id} -> template {self.template_id}"
