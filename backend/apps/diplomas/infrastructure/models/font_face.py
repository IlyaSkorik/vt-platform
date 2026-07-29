"""Persistence for one uploaded font face.

A row per **file**, not per family: a family is four files at most and the organizer uploads
them one at a time, so the row that can be added and removed is the face. The family is what
the catalog groups them into.

``family_key`` is the normalized spelling ("PT Sans" → "ptsans") and exists as its own column
because it is what uniqueness is decided on and what the renderer looks a family up by. A
functional index over a normalized expression would say the same thing less legibly, and this
column is written by exactly one place.
"""

from __future__ import annotations

from django.db import models

from apps.diplomas.domain.fonts import FontVariant

from .base import BasePersistenceModel

__all__ = ["FontFaceModel", "FontVariantChoices"]


class FontVariantChoices(models.TextChoices):
    """The four faces a family is used in (mirrors the domain ``FontVariant``)."""

    REGULAR = FontVariant.REGULAR.value, "Regular"
    BOLD = FontVariant.BOLD.value, "Bold"
    ITALIC = FontVariant.ITALIC.value, "Italic"
    BOLD_ITALIC = FontVariant.BOLD_ITALIC.value, "Bold Italic"


class FontFaceModel(BasePersistenceModel):
    """Database row for an uploaded font face (persistence only — no logic)."""

    #: As the file names itself, and as the editor shows it ("PT Sans").
    family = models.CharField(max_length=120)
    #: The normalized spelling uniqueness and lookup go through.
    family_key = models.CharField(max_length=120)
    variant = models.CharField(max_length=16, choices=FontVariantChoices.choices)
    #: The ``/media/…`` reference the file is read back by.
    file_reference = models.CharField(max_length=1024)
    #: What the organizer's file was called, so the library screen is recognisable to them.
    original_filename = models.CharField(max_length=255)
    size_bytes = models.PositiveIntegerField(default=0)

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_font_face"
        verbose_name = "font face"
        verbose_name_plural = "font faces"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["family_key"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(variant__in=FontVariantChoices.values),
                name="diplomas_font_variant_valid",
            ),
            # One file per family and variant. A second upload of the same face is refused
            # rather than overwriting: a template points at the family by name, and swapping
            # the file underneath it would change documents nobody asked to change.
            models.UniqueConstraint(
                fields=["family_key", "variant"],
                condition=models.Q(deleted_at__isnull=True),
                name="diplomas_font_unique_family_variant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.family} {self.variant}"
