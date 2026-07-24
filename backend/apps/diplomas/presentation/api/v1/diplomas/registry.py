"""Read/write helpers for the diploma registry REST surface.

Keeps the views thin: wires the application :class:`DiplomaService` to its Django
adapters and shapes the aggregate into the platform's camelCase payloads. The
snapshot is emitted verbatim (it is already resolved values).
"""

from __future__ import annotations

import uuid
from typing import Any

from django.utils import timezone

from apps.diplomas.application.services import DiplomaService
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource
from apps.diplomas.infrastructure.repositories import DjangoDiplomaRepository

__all__ = ["create_diploma", "get_diploma", "list_diplomas"]


def _service() -> DiplomaService:
    return DiplomaService(
        repository=DjangoDiplomaRepository(),
        snapshots=DjangoDiplomaSnapshotSource(),
    )


def _diploma_json(diploma: Diploma) -> dict[str, Any]:
    return {
        "id": str(diploma.id),
        "number": diploma.number,
        "verificationToken": diploma.verification_token,
        "competitionId": str(diploma.competition_id),
        "submissionId": str(diploma.submission_id),
        "templateId": str(diploma.template_id),
        "status": diploma.status.value,
        "snapshot": diploma.snapshot.to_dict(),
        "printPdfPath": diploma.print_pdf_path,
        "officialPdfPath": diploma.official_pdf_path,
        "issuedAt": diploma.issued_at,
        "createdAt": diploma.created_at,
        "updatedAt": diploma.updated_at,
    }


def create_diploma(*, submission_id: uuid.UUID, template_id: uuid.UUID) -> dict[str, Any]:
    """Create one diploma from a submission. May raise a ``DiplomaError``."""
    diploma = _service().create_diploma(submission_id=submission_id, template_id=template_id, now=timezone.now())
    return _diploma_json(diploma)


def get_diploma(diploma_id: uuid.UUID) -> dict[str, Any]:
    """One diploma's JSON. Raises ``DiplomaNotFoundError`` if unknown."""
    return _diploma_json(_service().get_diploma(diploma_id))


def list_diplomas(competition_id: uuid.UUID) -> list[dict[str, Any]]:
    """The competition's diploma registry (newest first)."""
    return [_diploma_json(diploma) for diploma in _service().list_for_competition(competition_id)]
