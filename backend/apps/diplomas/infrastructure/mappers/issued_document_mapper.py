"""``IssuedDocumentMapper`` — the ACL between ``IssuedDocument`` and its ORM row.

The single component that knows both the framework-free domain and the Django
``IssuedDocumentModel``. It serializes the snapshot to a JSON-safe document and
rehydrates it back via :meth:`IssuedDocument.rehydrate` (no re-validation, no
events).
"""

from __future__ import annotations

from typing import Any

from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.domain.issued_document import IssuedDocument
from apps.diplomas.domain.value_objects import DiplomaSnapshot
from apps.diplomas.infrastructure.models import IssuedDocumentModel

__all__ = ["IssuedDocumentMapper"]


class IssuedDocumentMapper:
    """Bidirectional, stateless translator between ``IssuedDocument`` and its row."""

    @staticmethod
    def to_domain(model: IssuedDocumentModel) -> IssuedDocument:
        return IssuedDocument.rehydrate(
            document_id=model.id,
            document_type=DocumentType(model.document_type),
            competition_id=model.competition_id,
            submission_id=model.submission_id,
            template_id=model.template_id,
            snapshot=DiplomaSnapshot.from_dict(model.snapshot or {}),
            created_at=model.created_at,
            updated_at=model.updated_at,
            recipient=model.recipient or "",
            category_id=model.category_id,
            pdf_path=model.pdf_path or None,
            published_at=model.published_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: IssuedDocument) -> IssuedDocumentModel:
        """Build a brand-new, **unsaved** ``IssuedDocumentModel`` from an aggregate."""
        return IssuedDocumentModel(**IssuedDocumentMapper._to_columns(entity))

    @staticmethod
    def update_model(model: IssuedDocumentModel, entity: IssuedDocument) -> IssuedDocumentModel:
        """Project ``entity`` onto an existing ``model`` in place, returning it."""
        for field, value in IssuedDocumentMapper._to_columns(entity).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def _to_columns(entity: IssuedDocument) -> dict[str, Any]:
        return {
            "id": entity.id,
            "document_type": entity.document_type.value,
            "competition_id": entity.competition_id,
            "submission_id": entity.submission_id,
            "template_id": entity.template_id,
            "recipient": entity.recipient,
            "category_id": entity.category_id,
            "snapshot": entity.snapshot.to_dict(),
            "pdf_path": entity.pdf_path or "",
            "published_at": entity.published_at,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "version": entity.version,
        }
