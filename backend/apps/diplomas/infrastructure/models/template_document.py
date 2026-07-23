"""``TemplateDocumentModel`` - the PDF a template is marked up over.

Persistence model only (no business logic). The PDF is the immutable *background*
of the future constructor: fields will live on a separate overlay, never on the
document itself. The file bytes are kept in ``default_storage`` (as everywhere in
this codebase); the row stores only the string ``file_reference`` (a ``/media/…``
path), mirroring the competitions regulation/poster uploads.

A template has at most one *current* document (the latest non-deleted row);
replacing the PDF soft-deletes the previous one, leaving room for versioning
(``TemplateVersion``) later.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["TemplateDocumentModel"]


class TemplateDocumentModel(BasePersistenceModel):
    """Database row for a template's backing PDF (persistence only)."""

    template = models.ForeignKey(
        "diplomas.TemplateModel",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    # A `/media/…` path served directly (see AllowMediaFramingMiddleware); not a FileField.
    file_reference = models.CharField(max_length=1024)
    original_filename = models.CharField(max_length=255, blank=True, default="")
    # Page count is resolved by the client-side viewer (pdf.js); 0 until known.
    page_count = models.PositiveIntegerField(default=0)

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_template_document"
        verbose_name = "template document"
        verbose_name_plural = "template documents"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["template"]),
        ]

    def __str__(self) -> str:
        return f"Document {self.id} for template {self.template_id}"
