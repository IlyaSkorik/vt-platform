"""The participant's documents read model — "Мои документы" in the cabinet.

A dedicated projection over everything the platform has issued to one applicant:
diplomas from the register and issued documents (thank-you letters today) from
their own table, presented as one flat list the cabinet renders directly.

Read-only, and deliberately *not* a second publication mechanism. A document
appears here exactly when its own rules say it is the participant's to see:

* a **diploma** once its official PDF exists — the pre-ceremony print copy is the
  organizer's working artifact and never reaches the cabinet;
* an **issued document** once it is published, which for a kind that publishes on
  generation is the moment it is rendered. That is what "the organizer publishes
  nothing extra" means in practice.

Layering: pure and framework-free. It defines the flat view DTO the presentation
edge serializes, the read-service port the composition root wires to a concrete
adapter, and the pure ordering/labelling rules — so those are unit tested without
a database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.diplomas.domain.document_types import DocumentType

__all__ = [
    "DOCUMENT_TYPE_ORDER",
    "ParticipantDocumentView",
    "ParticipantDocumentsReadService",
    "sort_documents",
]

#: Display order of the kinds in the cabinet: the award first, courtesies after.
#: A kind missing from this map sorts last, so a new type is visible rather than
#: hidden if someone forgets to rank it.
DOCUMENT_TYPE_ORDER: dict[DocumentType, int] = {
    DocumentType.DIPLOMA: 0,
    DocumentType.THANK_YOU: 1,
}


@dataclass(frozen=True, slots=True)
class ParticipantDocumentView:
    """One issued document as the participant's cabinet shows it.

    Flat and already-resolved: the values come from the document's own frozen
    snapshot, so the cabinet needs no further lookups and shows exactly what the
    document says.
    """

    id: uuid.UUID
    document_type: DocumentType
    #: Present only for register documents; ``None`` for unnumbered kinds.
    number: str | None
    participant_name: str | None
    competition_title: str | None
    nomination: str | None
    #: ``None`` until the jury has sat; only meaningful for kinds that award one.
    degree: str | None
    #: The stored ``/media/…`` reference the client resolves against the API origin.
    file_url: str
    issued_at: datetime | None


@runtime_checkable
class ParticipantDocumentsReadService(Protocol):
    """Port the cabinet reads through."""

    def list_for_applicant(self, applicant_id: uuid.UUID) -> list[ParticipantDocumentView]:
        """Every document this applicant may see, ready to render."""
        ...


def sort_documents(documents: list[ParticipantDocumentView]) -> list[ParticipantDocumentView]:
    """Order for display: by kind, then newest first within a kind.

    Pure, so the ordering is tested without a database. ``issued_at`` may be
    ``None``, which sorts last within its kind rather than blowing up on a
    comparison with a datetime.
    """
    return sorted(
        documents,
        key=lambda doc: (
            DOCUMENT_TYPE_ORDER.get(doc.document_type, len(DOCUMENT_TYPE_ORDER)),
            doc.issued_at is None,
            -(doc.issued_at.timestamp() if doc.issued_at is not None else 0.0),
        ),
    )
