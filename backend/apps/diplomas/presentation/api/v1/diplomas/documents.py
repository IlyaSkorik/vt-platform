"""Read/write helpers for the non-registry document REST surface.

Keeps the views thin: wires the composition root's
:class:`IssuedDocumentGenerationService` to the request and aggregates the
per-nomination outcomes into one summary.

Generation is synchronous, unlike the diploma print package. A thank-you run is a
render-and-store per performance with no numbering to serialize and no ZIP to
bundle, so there is nothing for a background job to buy here; if that changes, the
service is already the unit a Celery task would wrap.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.utils import timezone

from apps.diplomas.composition import build_issued_document_generation_service
from apps.diplomas.domain.document_types import DocumentType

__all__ = ["generate_documents"]


def generate_documents(
    *,
    competition_id: uuid.UUID,
    category_ids: list[uuid.UUID],
    document_type: str,
    force: bool = False,
) -> dict[str, Any]:
    """Generate one kind of document across the chosen nominations.

    Each nomination is generated from **its own** assigned template, so the run
    honours per-nomination designs rather than one competition-wide letter. May
    raise a ``DiplomaError`` (unassigned nomination, wrong template kind, template
    with no PDF) — the first failing nomination aborts the run.
    """
    service = build_issued_document_generation_service()
    kind = DocumentType(document_type)
    now = timezone.now()

    created = 0
    regenerated = 0
    without_recipient = 0
    for category_id in category_ids:
        result = service.generate_for_nomination(
            competition_id=competition_id,
            category_id=category_id,
            document_type=kind,
            now=now,
            force=force,
        )
        created += result.created
        regenerated += result.regenerated
        without_recipient += result.without_recipient

    return {
        "documentType": kind.value,
        "created": created,
        "regenerated": regenerated,
        "withoutRecipient": without_recipient,
        "nominations": len(category_ids),
    }
