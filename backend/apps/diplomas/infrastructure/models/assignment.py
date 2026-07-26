"""``AssignmentModel`` - binds a template to a (competition, nomination) pair.

Persistence model only (no business logic). This is the sole place a template
becomes tied to a competition: the constructor and the template library know
nothing about nominations.

Cross-context references are id-only (ARCH-001 §7.2): ``competition_id`` and
``category_id`` (the nomination) point at rows owned by the Competitions context
and are therefore plain ``UUIDField`` columns, **not** Django FKs. The link to the
template lives inside this context, so it is a real FK (``PROTECT`` — a template
in use cannot be deleted out from under its assignments).

The shape is unchanged from the original design — still one row per nomination per
*kind* of document. ``document_type`` names the kind, so a nomination holds one
diploma template **and** one thank-you template as two rows rather than one row
gaining columns:

    Вокал ──┬── DIPLOMA   → «Диплом танцы»
            └── THANK_YOU → «Благодарность синяя»

The kind is stored here rather than read from ``template.type`` because uniqueness
has to be a database constraint, and a Postgres unique constraint cannot join to
the template row to find its type. The two must agree, which the application
asserts on write (:class:`~apps.diplomas.domain.exceptions.TemplateTypeMismatchError`).
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel
from .document_type import DocumentTypeChoices

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

    # Which document slot of the nomination this assignment fills. Must equal the
    # assigned template's own ``type``.
    document_type = models.CharField(max_length=32, choices=DocumentTypeChoices.choices)

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_assignment"
        verbose_name = "template assignment"
        verbose_name_plural = "template assignments"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
            models.Index(fields=["template"]),
            models.Index(fields=["competition_id", "document_type"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            # One template per nomination per kind of document.
            models.UniqueConstraint(
                fields=["competition_id", "category_id", "document_type"],
                condition=models.Q(deleted_at__isnull=True),
                name="diplomas_unique_assignment_per_type",
            ),
            models.CheckConstraint(
                condition=models.Q(document_type__in=DocumentTypeChoices.values),
                name="diplomas_assignment_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Assignment {self.id} -> {self.document_type} template {self.template_id}"
