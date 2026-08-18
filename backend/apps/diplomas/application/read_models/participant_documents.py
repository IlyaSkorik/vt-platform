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
    "archive_entry_name",
    "archive_filename",
    "bundled_documents",
    "sort_documents",
]

#: Display order of the kinds in the cabinet: the award first, courtesies after.
#: A kind missing from this map sorts last, so a new type is visible rather than
#: hidden if someone forgets to rank it.
DOCUMENT_TYPE_ORDER: dict[DocumentType, int] = {
    DocumentType.DIPLOMA: 0,
    # The individual diplomas sit right under the collective's own, because that is the
    # order they are read in: what the ensemble won, then who was in it.
    DocumentType.INDIVIDUAL_DIPLOMA: 1,
    DocumentType.THANK_YOU: 2,
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
    #: The entry this document was issued for. Carried so the cabinet can group the
    #: documents of one performance together — an ensemble's twelve individual
    #: diplomas are one bundle, and grouping them by name or nomination would merge
    #: two entries that happen to share those.
    submission_id: uuid.UUID
    #: Present only for register documents; ``None`` for unnumbered kinds.
    number: str | None
    participant_name: str | None
    competition_title: str | None
    nomination: str | None
    #: ``None`` until the jury has sat; only meaningful for kinds that award one.
    degree: str | None
    #: Who the document is addressed to, for kinds issued per person. Empty for a
    #: document that belongs to the performance itself, like a diploma. It is what
    #: tells two thank-you letters on one entry apart.
    recipient: str
    #: The stored ``/media/…`` reference the client resolves against the API origin.
    file_url: str
    issued_at: datetime | None


@runtime_checkable
class ParticipantDocumentsReadService(Protocol):
    """Port the cabinet reads through."""

    def list_for_applicant(self, applicant_id: uuid.UUID) -> list[ParticipantDocumentView]:
        """Every document this applicant may see, ready to render."""
        ...


def bundled_documents(
    documents: list[ParticipantDocumentView],
    *,
    submission_id: uuid.UUID,
    document_type: DocumentType,
) -> list[ParticipantDocumentView]:
    """The documents of one entry and one kind, in the order the cabinet lists them.

    The whole selection rule of the archive, kept here so it is the same rule the list
    is rendered from: the caller hands in *its own* documents (the read service never
    returns anybody else's), and this narrows them to one bundle. A submission id that
    is not the caller's therefore yields nothing rather than someone else's diplomas —
    the scoping is a property of the input, not a check that can be forgotten.
    """
    return sort_documents([doc for doc in documents if doc.submission_id == submission_id and doc.document_type is document_type])


def archive_entry_name(document: ParticipantDocumentView, *, position: int) -> str:
    """What one document is called inside the archive.

    Named after the person it is for, because that is how whoever downloaded it hands
    the sheets out; the number follows so two people with the same name still get two
    files, and the position leads so the order in the folder is the order in the
    cabinet rather than the alphabet. A document addressed to nobody falls back to the
    performer named on it.
    """
    who = document.recipient.strip() or (document.participant_name or "").strip()
    parts = [f"{position:02d}", who or "Без имени"]
    if document.number:
        parts.append(document.number)
    return f"{' — '.join(parts)}.pdf"


def archive_filename(documents: list[ParticipantDocumentView], *, label: str) -> str:
    """The archive's own name: what it holds, and which festival it is from.

    The competition comes from the documents themselves — a participant downloading
    two bundles a year apart needs to tell them apart in a downloads folder.
    """
    festival = next((doc.competition_title for doc in documents if doc.competition_title), None)
    return f"{label} — {festival}.zip" if festival else f"{label}.zip"


def sort_documents(documents: list[ParticipantDocumentView]) -> list[ParticipantDocumentView]:
    """Order for display: by kind, newest first within a kind, then by recipient.

    Pure, so the ordering is tested without a database. ``issued_at`` may be
    ``None``, which sorts last within its kind rather than blowing up on a
    comparison with a datetime.

    The recipient breaks the remaining tie, and has to: one publication issues an
    ensemble's individual diplomas in the same instant, so timestamp alone left twelve
    rows in whatever order the database happened to return them — different on every
    request, and different again inside the archive built from them.
    """
    return sorted(
        documents,
        key=lambda doc: (
            DOCUMENT_TYPE_ORDER.get(doc.document_type, len(DOCUMENT_TYPE_ORDER)),
            doc.issued_at is None,
            -(doc.issued_at.timestamp() if doc.issued_at is not None else 0.0),
            doc.recipient.casefold(),
        ),
    )
