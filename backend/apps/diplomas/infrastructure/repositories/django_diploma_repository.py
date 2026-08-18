"""Django adapter implementing the ``DiplomaRepository`` port.

Numbers are **not** minted here: they come from the dedicated, row-locked counter
behind :class:`~apps.diplomas.infrastructure.repositories.DjangoDiplomaNumberSequence`
(no ``max(number) + 1`` scan, which could not be made parallel-safe). The
unconditional unique constraint on ``number`` remains the correctness backstop: a
duplicate would surface as an ``IntegrityError`` rather than two equal numbers.
"""

from __future__ import annotations

import uuid

from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.infrastructure.mappers import DiplomaMapper
from apps.diplomas.infrastructure.models import DiplomaModel
from apps.diplomas.infrastructure.models.base import uuid7

__all__ = ["DjangoDiplomaRepository"]


class DjangoDiplomaRepository:
    """Concrete ``DiplomaRepository`` over the Django ORM."""

    def new_id(self) -> uuid.UUID:
        return uuid7()

    def exists_for_submission(self, submission_id: uuid.UUID, document_type: DocumentType = DocumentType.DIPLOMA, recipient: str = "") -> bool:
        return DiplomaModel.objects.filter(
            submission_id=submission_id,
            document_type=document_type.value,
            recipient=recipient,
            deleted_at__isnull=True,
        ).exists()

    def add(self, diploma: Diploma) -> None:
        DiplomaMapper.to_model(diploma).save(force_insert=True)

    def update(self, diploma: Diploma) -> None:
        model = DiplomaModel.objects.filter(id=diploma.id).first()
        if model is None:
            return
        DiplomaMapper.update_model(model, diploma).save()

    def get(self, diploma_id: uuid.UUID) -> Diploma | None:
        model = DiplomaModel.objects.filter(id=diploma_id, deleted_at__isnull=True).first()
        return DiplomaMapper.to_domain(model) if model is not None else None

    def get_by_submission(
        self,
        submission_id: uuid.UUID,
        document_type: DocumentType = DocumentType.DIPLOMA,
        recipient: str = "",
    ) -> Diploma | None:
        """The one live diploma of this kind, for this performance and recipient.

        Scoped by kind and recipient rather than by submission alone: since individual
        diplomas share this table, an unscoped read would hand back an ensemble
        member's diploma when the caller asked for the collective's.
        """
        model = DiplomaModel.objects.filter(
            submission_id=submission_id,
            document_type=document_type.value,
            recipient=recipient,
            deleted_at__isnull=True,
        ).first()
        return DiplomaMapper.to_domain(model) if model is not None else None

    def list_by_competition(self, competition_id: uuid.UUID) -> list[Diploma]:
        rows = DiplomaModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).order_by("-created_at")
        return [DiplomaMapper.to_domain(row) for row in rows]
