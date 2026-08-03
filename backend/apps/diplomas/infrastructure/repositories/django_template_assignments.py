"""Django adapter implementing the ``TemplateAssignments`` read port.

Resolves "which template fills this nomination's slot for this kind of document?"
It reports the assigned template's **own** declared type alongside its id, so the
caller can check that the two agree — they are stored in separate columns (the
assignment names the slot, the template names what it was authored for) precisely
because a Postgres unique constraint cannot join to the template row.
"""

from __future__ import annotations

import uuid

from apps.diplomas.application.interfaces import AssignedTemplate
from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.infrastructure.models import AssignmentModel

__all__ = ["DjangoTemplateAssignments"]


class DjangoTemplateAssignments:
    """Concrete ``TemplateAssignments`` over the Django ORM."""

    def for_nomination(self, *, competition_id: uuid.UUID, category_id: uuid.UUID, document_type: DocumentType) -> AssignedTemplate | None:
        row = (
            AssignmentModel.objects.filter(
                competition_id=competition_id,
                category_id=category_id,
                document_type=document_type.value,
                deleted_at__isnull=True,
            )
            .select_related("template")
            .first()
        )
        if row is None or row.template.deleted_at is not None:
            return None
        return AssignedTemplate(
            template_id=row.template_id,
            template_type=DocumentType(row.template.type),
        )
