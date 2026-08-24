"""``TemplateModel`` - persistence representation of a document template.

Persistence model only (no business logic). A template is a **self-contained,
user-owned** entity: the organizer creates and names every template in their
library — the system seeds nothing and imposes no naming or structure. A template
belongs to no competition and no nomination; the binding to a competition/nomination
lives entirely in ``AssignmentModel``, so one template can be reused across many
competitions and seasons.

"User-owned" is load-bearing since the platform hosts several organizations:
``organizer_id`` names the one whose library this template is in. It is the
boundary, not a label — an organizer authors, edits and assigns their own
templates and never sees anyone else's. Reuse "across many competitions and
seasons" therefore means across *their* competitions and seasons.

``type`` declares which kind of document the template produces (diploma, thank-you
letter, …). It is required: a layout is authored for one kind — a diploma carries a
degree field and a QR block, a thank-you letter carries neither — so a template
with no declared kind could not be safely rendered as anything.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel
from .document_type import DocumentTypeChoices

__all__ = ["TemplateModel"]


class TemplateModel(BasePersistenceModel):
    """Database row for a document template (persistence only - no business logic)."""

    # The organization whose library this template belongs to. An id-only
    # cross-context reference (ARCH-001 §7.2) — the row it names is owned by the
    # Organization context, so this is a plain UUIDField and not a Django FK.
    #
    # Non-nullable on purpose. A template with no owner is reachable by everyone,
    # which is the bug this column exists to close; leaving NULL representable
    # would keep a way back into it. The platform operator is staff of no
    # organization and so does not author templates — they read across libraries,
    # which is a scoping question rather than an ownership one.
    organizer_id = models.UUIDField()

    name = models.CharField(max_length=160)
    description = models.CharField(max_length=500, blank=True, default="")

    # Which kind of document this template produces. No model-level default: the
    # caller must decide, so a new template cannot silently become a diploma.
    # (The migration backfills existing rows as DIPLOMA, which is what they are.)
    type = models.CharField(max_length=32, choices=DocumentTypeChoices.choices)

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_template"
        verbose_name = "document template"
        verbose_name_plural = "document templates"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["organizer_id"]),
            # Every listing is "this organization's templates, of this kind" — the
            # library page and the nomination's thank-you slot both.
            models.Index(fields=["organizer_id", "type"]),
            models.Index(fields=["name"]),
            models.Index(fields=["type"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(type__in=DocumentTypeChoices.values),
                name="diplomas_template_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"
