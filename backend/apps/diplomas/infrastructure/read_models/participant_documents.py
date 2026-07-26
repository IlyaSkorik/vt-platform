"""ORM-backed adapter for the participant's documents read model.

Two indexed reads — the diploma register and the issued-document table — joined in
memory on the applicant's own submissions, then ordered by the pure
:func:`sort_documents`.

Finding "this applicant's performances" needs the Applications context, which the
Diplomas context already reads by id through its ACL (ARCH-001 §7.2). That read is
narrowed to submission ids and nothing else: the document facts themselves come
from each document's frozen snapshot, never from the live submission, so a renamed
participant does not change an issued document.
"""

from __future__ import annotations

import uuid

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.diplomas.application.read_models.participant_documents import (
    ParticipantDocumentView,
    sort_documents,
)
from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.domain.value_objects import DiplomaSnapshot
from apps.diplomas.infrastructure.models import DiplomaModel, IssuedDocumentModel

__all__ = ["DjangoParticipantDocumentsReader"]


def _nomination(snapshot: DiplomaSnapshot) -> str | None:
    """The nomination title as printed, falling back to its discipline."""
    return snapshot.nomination.title or snapshot.nomination.discipline


class DjangoParticipantDocumentsReader:
    """Concrete ``ParticipantDocumentsReadService`` over the Django ORM."""

    def list_for_applicant(self, applicant_id: uuid.UUID) -> list[ParticipantDocumentView]:
        submission_ids = list(
            SubmissionModel.objects.filter(
                applicant_id=applicant_id, deleted_at__isnull=True
            ).values_list("id", flat=True)
        )
        if not submission_ids:
            return []

        documents: list[ParticipantDocumentView] = []

        # Diplomas: visible once the official PDF exists. The print copy is the
        # organizer's pre-ceremony artifact and is deliberately excluded.
        diplomas = DiplomaModel.objects.filter(
            submission_id__in=submission_ids,
            deleted_at__isnull=True,
        ).exclude(official_pdf_path="")
        for row in diplomas:
            snapshot = DiplomaSnapshot.from_dict(row.snapshot or {})
            documents.append(
                ParticipantDocumentView(
                    id=row.id,
                    document_type=DocumentType.DIPLOMA,
                    number=row.number,
                    participant_name=snapshot.participant.display_name or None,
                    competition_title=snapshot.competition.title,
                    nomination=_nomination(snapshot),
                    degree=snapshot.award.degree,
                    file_url=row.official_pdf_path,
                    issued_at=row.issued_at or row.updated_at,
                )
            )

        # Issued documents: visible once published, which for a kind that
        # publishes on generation is the moment it was rendered.
        issued = IssuedDocumentModel.objects.filter(
            submission_id__in=submission_ids,
            deleted_at__isnull=True,
            published_at__isnull=False,
        ).exclude(pdf_path="")
        for row in issued:
            snapshot = DiplomaSnapshot.from_dict(row.snapshot or {})
            documents.append(
                ParticipantDocumentView(
                    id=row.id,
                    document_type=DocumentType(row.document_type),
                    number=None,
                    participant_name=snapshot.participant.display_name or None,
                    competition_title=snapshot.competition.title,
                    nomination=_nomination(snapshot),
                    degree=None,
                    file_url=row.pdf_path,
                    issued_at=row.published_at,
                )
            )

        return sort_documents(documents)
