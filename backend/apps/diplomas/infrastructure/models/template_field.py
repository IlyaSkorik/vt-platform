"""``TemplateFieldModel`` - a field placed on a template's overlay.

Persistence model only (no business logic). Fields are the editor's saved layout:
each one positions an element over the (immutable) PDF background. Coordinates are
**normalised** (0..1) relative to the page, so they survive zoom and any display
resolution. Persisted/loaded as a whole layout (atomic replace) — mirroring how
visual editors save a document — never one request per drag.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["TemplateFieldModel"]


class TemplateFieldModel(BasePersistenceModel):
    """Database row for a placed template field (persistence only)."""

    template = models.ForeignKey(
        "diplomas.TemplateModel",
        on_delete=models.CASCADE,
        related_name="fields",
    )
    # 1-based page the field lives on.
    page = models.PositiveIntegerField()
    # Element kind (mirrors the frontend field-type catalogue, e.g. "participant_name").
    type = models.CharField(max_length=32)
    # Data-source reference resolved at generation (e.g. "participant.display_name").
    # A field is either data-bound (binding set, value empty) or free (value set,
    # binding empty).
    binding = models.CharField(max_length=64, blank=True, default="")
    # Own text for a free-text field; empty for a data-bound field.
    value = models.TextField(blank=True, default="")
    # Normalised box (0..1) relative to the page.
    x = models.FloatField()
    y = models.FloatField()
    width = models.FloatField()
    height = models.FloatField()
    # Reserved for a later stage — always 0 for now.
    rotation = models.FloatField(default=0)
    # Stacking / z-order within a page.
    sort_order = models.PositiveIntegerField(default=0)
    # Appearance (font, colour, alignment, …) as one document — kept flexible so
    # new appearance options need no migration.
    style = models.JSONField(default=dict, blank=True)
    # Per-field configuration for composite fields (e.g. the nomination block's
    # chosen parts and prefix). Empty for simple fields. A JSON document so new
    # composite kinds need no migration.
    config = models.JSONField(default=dict, blank=True)

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_template_field"
        verbose_name = "template field"
        verbose_name_plural = "template fields"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["template", "page"]),
        ]

    def __str__(self) -> str:
        return f"Field {self.id} ({self.type}) on template {self.template_id}"
