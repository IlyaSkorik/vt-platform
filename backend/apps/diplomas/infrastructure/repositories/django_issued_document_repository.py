"""Django adapter implementing the ``IssuedDocumentRepository`` port.

No numbering and no token minting: an issued document is defined by having neither
(see :mod:`apps.diplomas.domain.document_types`). Two unique constraints are the
correctness backstop, and which one applies depends on how the kind is addressed:
``(submission_id, document_type, recipient)`` for a kind issued once per
performance, and ``(competition_id, category_id, document_type, recipient)`` for
one addressed to a person — a double generation surfaces as an ``IntegrityError``
rather than as a second thank-you letter for the same teacher.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from django.db.models import Q

from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.domain.issued_document import IssuedDocument
from apps.diplomas.infrastructure.mappers import IssuedDocumentMapper
from apps.diplomas.infrastructure.models import IssuedDocumentModel
from apps.diplomas.infrastructure.models.base import uuid7

__all__ = ["DjangoIssuedDocumentRepository"]


class DjangoIssuedDocumentRepository:
    """Concrete ``IssuedDocumentRepository`` over the Django ORM."""

    def new_id(self) -> uuid.UUID:
        return uuid7()

    def add(self, document: IssuedDocument) -> None:
        IssuedDocumentMapper.to_model(document).save(force_insert=True)

    def update(self, document: IssuedDocument) -> None:
        model = IssuedDocumentModel.objects.filter(id=document.id).first()
        if model is None:
            return
        IssuedDocumentMapper.update_model(model, document).save()

    def get_for_submission(self, submission_id: uuid.UUID, document_type: DocumentType, recipient: str = "") -> IssuedDocument | None:
        """The live document of this kind for a performance and recipient, or None.

        ``recipient`` is empty for a kind issued once per performance; for a
        per-teacher kind it distinguishes one teacher's letter from another's.
        """
        model = IssuedDocumentModel.objects.filter(
            submission_id=submission_id,
            document_type=document_type.value,
            recipient=recipient,
            deleted_at__isnull=True,
        ).first()
        return IssuedDocumentMapper.to_domain(model) if model is not None else None

    def list_for_genre(
        self,
        *,
        competition_id: uuid.UUID,
        category_id: uuid.UUID,
        document_type: DocumentType,
        submission_ids: Sequence[uuid.UUID],
    ) -> list[IssuedDocument]:
        """Every live document of this kind the genre already holds, oldest first.

        One query for the whole run rather than one per recipient, and it has to
        reach rows written before the genre was part of a document's identity —
        those carry no ``category_id`` and are recognised by the entry they are
        anchored to. Oldest first so that, where a genre somehow holds two for one
        person, the run keeps the one whose URL has been in circulation longest.
        """
        rows = IssuedDocumentModel.objects.filter(
            Q(category_id=category_id) | Q(category_id__isnull=True, submission_id__in=list(submission_ids)),
            competition_id=competition_id,
            document_type=document_type.value,
            deleted_at__isnull=True,
        ).order_by("created_at")
        return [IssuedDocumentMapper.to_domain(row) for row in rows]

    def list_by_competition(self, competition_id: uuid.UUID, document_type: DocumentType) -> list[IssuedDocument]:
        """Every live document of this kind for a competition, newest first."""
        rows = IssuedDocumentModel.objects.filter(
            competition_id=competition_id,
            document_type=document_type.value,
            deleted_at__isnull=True,
        ).order_by("-created_at")
        return [IssuedDocumentMapper.to_domain(row) for row in rows]
