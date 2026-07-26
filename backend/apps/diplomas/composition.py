"""Composition root for the Diplomas bounded context.

The one place a framework-free use case or read model is wired to its concrete
infrastructure adapter (ARCH-001 §7.3, Dependency Inversion): the presentation
edge asks here for an assembled handler and stays ignorant of which repository or
reader sits behind the port. Adapters are stateless and cheap, so they are
assembled per call.

Not to be confused with
:mod:`apps.diplomas.presentation.api.v1.diplomas.composition`, which is about
*composing a diploma template* (its document and field layout) — a different
sense of the word entirely.
"""

from __future__ import annotations

from apps.diplomas.application.issued_documents import IssuedDocumentGenerationService
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource
from apps.diplomas.infrastructure.pdf.workspace import DjangoPrintPackageWorkspace
from apps.diplomas.infrastructure.read_models import (
    DjangoDiplomaVerificationReader,
    DjangoParticipantDocumentsReader,
)
from apps.diplomas.infrastructure.repositories import (
    DjangoIssuedDocumentRepository,
    DjangoTemplateAssignments,
)

__all__ = [
    "build_diploma_verification_read_service",
    "build_issued_document_generation_service",
    "build_participant_documents_read_service",
]


def build_diploma_verification_read_service() -> DjangoDiplomaVerificationReader:
    """Assemble the public diploma verification read model (QR authenticity page)."""
    return DjangoDiplomaVerificationReader()


def build_participant_documents_read_service() -> DjangoParticipantDocumentsReader:
    """Assemble the participant's "Мои документы" read model."""
    return DjangoParticipantDocumentsReader()


def build_issued_document_generation_service() -> IssuedDocumentGenerationService:
    """Assemble generation for non-registry documents (thank-you letters today).

    Deliberately shares the diploma pipeline's adapters — the same snapshot ACL and
    the same render/store workspace — so the two paths cannot drift in how a
    document is built from a submission.
    """
    return IssuedDocumentGenerationService(
        repository=DjangoIssuedDocumentRepository(),
        snapshots=DjangoDiplomaSnapshotSource(),
        workspace=DjangoPrintPackageWorkspace(),
        assignments=DjangoTemplateAssignments(),
    )
