"""Django adapter implementing the ``TemplateAssignments`` read port.

Resolves "which template does this genre print this kind of document on?" — one
answer for the genre and one for each of its nominations that assigns a template
of its own. It reports every template's **own** declared type alongside its id, so
the caller can check that the two agree — they are stored in separate columns (the
assignment names the slot, the template names what it was authored for) precisely
because a Postgres unique constraint cannot join to the template row.
"""

from __future__ import annotations

import uuid

from apps.diplomas.application.interfaces import AssignedTemplate, NominationTemplates
from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.infrastructure.models import AssignmentModel

__all__ = ["DjangoTemplateAssignments"]


class DjangoTemplateAssignments:
    """Concrete ``TemplateAssignments`` over the Django ORM."""

    def for_category(self, *, competition_id: uuid.UUID, category_id: uuid.UUID, document_type: DocumentType) -> NominationTemplates:
        rows = (
            AssignmentModel.objects.filter(
                competition_id=competition_id,
                category_id=category_id,
                document_type=document_type.value,
                deleted_at__isnull=True,
            )
            .select_related("template")
            # The whole genre in one query: both levels are the same three columns
            # apart, and generation needs them together anyway.
            .order_by("discipline_id")
        )
        default: AssignedTemplate | None = None
        by_discipline: dict[uuid.UUID, AssignedTemplate] = {}
        for row in rows:
            if row.template.deleted_at is not None:
                # A soft-deleted template is no template at all. Dropped rather than
                # reported, so a genre whose default was deleted falls through to the
                # same "nothing assigned" answer it would give had it never had one.
                continue
            assigned = AssignedTemplate(template_id=row.template_id, template_type=DocumentType(row.template.type))
            if row.discipline_id is None:
                default = assigned
            else:
                by_discipline[row.discipline_id] = assigned
        return NominationTemplates(default=default, by_discipline=by_discipline)
