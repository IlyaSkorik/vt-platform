"""``TemplateModel`` - persistence representation of a diploma template.

Persistence model only (no business logic). A template is a **self-contained,
user-owned** entity: the organizer creates and names every template in their
library — the system seeds nothing and imposes no naming or structure. A template
belongs to no competition and no nomination; the binding to a competition/nomination
lives entirely in ``AssignmentModel``, so one template can be reused across many
competitions, seasons and document types.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["TemplateModel"]


class TemplateModel(BasePersistenceModel):
    """Database row for a diploma template (persistence only - no business logic)."""

    name = models.CharField(max_length=160)
    description = models.CharField(max_length=500, blank=True, default="")

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_template"
        verbose_name = "diploma template"
        verbose_name_plural = "diploma templates"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name
