"""Read/write helpers for the non-registry document REST surface.

Keeps the views thin: wires the composition root's
:class:`IssuedDocumentGenerationService` to the request and aggregates the
per-nomination outcomes into one summary.

Generation is synchronous, unlike the diploma print package: a thank-you run has
no number to reserve, so there is nothing for a background job to serialize. The
optional ZIP is bundled in the same request — if that ever grows too slow for one,
the service is already the unit a Celery task would wrap.
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
    bundle: bool = False,
    publish: bool = True,
) -> dict[str, Any]:
    """Generate one kind of document across the chosen nominations.

    Each nomination is generated from **its own** assigned template, so the run
    honours per-nomination designs rather than one competition-wide letter. May
    raise a ``DiplomaError`` (unassigned nomination, wrong template kind, template
    with no PDF) — the first failing nomination aborts the run.

    Two independent switches, because the organizer's two intents are independent:
    ``publish`` shows the documents to the participants, ``bundle`` hands back a ZIP
    to print from (in ``zipUrl``). Preparing a print run therefore leaves the
    cabinets untouched, and a later publishing run publishes what it finds without
    re-rendering it. Publication is never withdrawn by a subsequent run.
    """
    service = build_issued_document_generation_service()
    kind = DocumentType(document_type)
    now = timezone.now()

    created = 0
    regenerated = 0
    without_recipient = 0
    published = 0
    items: list[tuple[str, str]] = []
    for category_id in category_ids:
        result = service.generate_for_nomination(
            competition_id=competition_id,
            category_id=category_id,
            document_type=kind,
            now=now,
            force=force,
            publish=publish,
        )
        created += result.created
        regenerated += result.regenerated
        without_recipient += result.without_recipient
        published += result.published
        items.extend(result.items)

    # No documents at all means nothing to print: an empty archive would only give
    # the organizer a broken download to puzzle over.
    zip_url = (
        service.bundle(competition_id=competition_id, document_type=kind, items=items)
        if bundle and items
        else None
    )

    return {
        "documentType": kind.value,
        "created": created,
        "regenerated": regenerated,
        "withoutRecipient": without_recipient,
        "nominations": len(category_ids),
        "documents": len(items),
        "published": published,
        "zipUrl": zip_url,
    }
