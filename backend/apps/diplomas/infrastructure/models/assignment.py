"""``AssignmentModel`` - binds a template to a nomination of a competition.

Persistence model only (no business logic). This is the sole place a template
becomes tied to a competition: the constructor and the template library know
nothing about nominations.

Cross-context references are id-only (ARCH-001 §7.2): ``competition_id``,
``category_id`` (the genre) and ``discipline_id`` (the nomination inside it) point
at rows owned by the Competitions context and are therefore plain ``UUIDField``
columns, **not** Django FKs. The link to the template lives inside this context, so
it is a real FK (``PROTECT`` — a template in use cannot be deleted out from under
its assignments).

**Two levels, one table.** ``discipline_id`` is nullable, and the two states are
different decisions rather than a filled-in and a missing field:

* ``NULL`` — the genre's default. Every entry of the genre prints on it.
* a discipline — that one nomination prints on it instead, whatever the genre says.

The festival asked for this: a genre's nominations are often judged by different
juries, so the sheets they sign differ even though the genre is one. Resolution is
therefore "the nomination's own template, else the genre's" — see
``TemplateAssignments.for_category``.

The shape is otherwise unchanged — still one row per nomination per *kind* of
document. ``document_type`` names the kind, so a nomination holds one diploma
template **and** one thank-you template as two rows rather than one row gaining
columns:

    Вокал ──┬── DIPLOMA   → «Диплом танцы»
            ├── THANK_YOU → «Благодарность синяя»
            └── Эстрадный вокал ── DIPLOMA → «Диплом эстрада»

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
    # The genre the assignment applies to. Genre == Category in the Competitions
    # context (see apps.competitions ... CategoryModel).
    category_id = models.UUIDField()
    # The one nomination of that genre the assignment is narrowed to, or NULL for
    # the genre's default. Nomination == Discipline in the Competitions context,
    # which also owns the rule that a discipline belongs to exactly one category —
    # so ``category_id`` here is the discipline's own genre, never a second choice.
    discipline_id = models.UUIDField(null=True, blank=True, default=None)
    template = models.ForeignKey(
        "diplomas.TemplateModel",
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    # Which document slot of the genre (or nomination) this assignment fills. Must
    # equal the assigned template's own ``type``.
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
            # Resolution reads one genre's rows of one kind and picks the nomination's
            # own row over the default, so that triple is the lookup, not the id.
            models.Index(fields=["competition_id", "category_id", "document_type"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            # One default template per genre per kind of document. Split in two by
            # level rather than written as one constraint over four columns, because
            # SQL unique constraints treat NULLs as distinct: a single constraint
            # including ``discipline_id`` would let a genre hold any number of
            # defaults. The two conditions partition the table, so each level keeps
            # its own "only one" rule.
            models.UniqueConstraint(
                fields=["competition_id", "category_id", "document_type"],
                condition=models.Q(deleted_at__isnull=True, discipline_id__isnull=True),
                name="diplomas_unique_assignment_per_type",
            ),
            # ...and one per nomination per kind, alongside (not instead of) the
            # genre's default: the override is what makes them differ.
            models.UniqueConstraint(
                fields=["competition_id", "category_id", "discipline_id", "document_type"],
                condition=models.Q(deleted_at__isnull=True, discipline_id__isnull=False),
                name="diplomas_unique_assignment_per_discipline",
            ),
            models.CheckConstraint(
                condition=models.Q(document_type__in=DocumentTypeChoices.values),
                name="diplomas_assignment_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Assignment {self.id} -> {self.document_type} template {self.template_id}"
