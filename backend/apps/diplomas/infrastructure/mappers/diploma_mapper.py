"""``DiplomaMapper`` — the ACL between the ``Diploma`` aggregate and its ORM row.

The single component that knows both the framework-free domain and the Django
``DiplomaModel``. It serializes the snapshot to a JSON-safe document and rehydrates
it back via :meth:`Diploma.rehydrate` (no re-validation, no events).
"""

from __future__ import annotations

from typing import Any

from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.value_objects import DiplomaSnapshot, DiplomaStatus
from apps.diplomas.infrastructure.models import DiplomaModel

__all__ = ["DiplomaMapper"]


class DiplomaMapper:
    """Bidirectional, stateless translator between ``Diploma`` and its row."""

    @staticmethod
    def to_domain(model: DiplomaModel) -> Diploma:
        return Diploma.rehydrate(
            diploma_id=model.id,
            number=model.number,
            verification_token=model.verification_token,
            competition_id=model.competition_id,
            submission_id=model.submission_id,
            template_id=model.template_id,
            status=DiplomaStatus(model.status),
            document_type=DocumentType(model.document_type or DocumentType.DIPLOMA.value),
            recipient=model.recipient or "",
            snapshot=DiplomaSnapshot.from_dict(model.snapshot or {}),
            created_at=model.created_at,
            updated_at=model.updated_at,
            print_pdf_path=model.print_pdf_path or None,
            official_pdf_path=model.official_pdf_path or None,
            issued_at=model.issued_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: Diploma) -> DiplomaModel:
        """Build a brand-new, **unsaved** ``DiplomaModel`` from an aggregate."""
        return DiplomaModel(**DiplomaMapper._to_columns(entity))

    @staticmethod
    def update_model(model: DiplomaModel, entity: Diploma) -> DiplomaModel:
        """Project ``entity`` onto an existing ``model`` in place, returning it."""
        for field, value in DiplomaMapper._to_columns(entity).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def _to_columns(entity: Diploma) -> dict[str, Any]:
        return {
            "id": entity.id,
            "number": entity.number,
            "verification_token": entity.verification_token,
            "competition_id": entity.competition_id,
            "submission_id": entity.submission_id,
            "template_id": entity.template_id,
            "status": entity.status.value,
            "document_type": entity.document_type.value,
            "recipient": entity.recipient,
            "snapshot": entity.snapshot.to_dict(),
            "print_pdf_path": entity.print_pdf_path or "",
            "official_pdf_path": entity.official_pdf_path or "",
            "issued_at": entity.issued_at,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "version": entity.version,
        }
