"""The ``IssuedDocument`` aggregate — a generated document that is not a diploma.

Hosts every document kind whose :class:`~apps.diplomas.domain.document_types.DocumentPolicy`
asks for neither a number nor verification: today the thank-you letter, tomorrow a
certificate. The ``Diploma`` aggregate keeps the numbered, verifiable registry to
itself and is untouched by this.

Like a diploma, an issued document is **self-contained**: it freezes the
:class:`DiplomaSnapshot` it was generated from, so later edits to the submission or
the competition never change it. Unlike a diploma it has no number, no verification
token and no public register entry — and when its policy says so, it is published
the moment it is generated, with no separate organizer step.

Framework-free (no Django). Persistence lives in the infrastructure mapper.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime

from apps.diplomas.domain.document_types import DocumentType, policy_for
from apps.diplomas.domain.value_objects import DiplomaSnapshot

__all__ = ["IssuedDocument"]


@dataclass(frozen=True, slots=True)
class IssuedDocument:
    """One generated document. Immutable value semantics; transitions return a new one."""

    id: uuid.UUID
    document_type: DocumentType
    competition_id: uuid.UUID
    submission_id: uuid.UUID
    template_id: uuid.UUID
    snapshot: DiplomaSnapshot
    created_at: datetime
    updated_at: datetime
    pdf_path: str | None = None
    published_at: datetime | None = None
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        document_id: uuid.UUID,
        document_type: DocumentType,
        competition_id: uuid.UUID,
        submission_id: uuid.UUID,
        template_id: uuid.UUID,
        snapshot: DiplomaSnapshot,
        now: datetime,
    ) -> IssuedDocument:
        """Create a document with no PDF yet and no publication.

        Rendering follows; :meth:`with_pdf` records the result and applies the
        kind's publication rule.
        """
        return cls(
            id=document_id,
            document_type=document_type,
            competition_id=competition_id,
            submission_id=submission_id,
            template_id=template_id,
            snapshot=snapshot,
            created_at=now,
            updated_at=now,
            pdf_path=None,
            published_at=None,
            version=1,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        document_id: uuid.UUID,
        document_type: DocumentType,
        competition_id: uuid.UUID,
        submission_id: uuid.UUID,
        template_id: uuid.UUID,
        snapshot: DiplomaSnapshot,
        created_at: datetime,
        updated_at: datetime,
        pdf_path: str | None,
        published_at: datetime | None,
        version: int,
    ) -> IssuedDocument:
        """Reconstruct from persistence (no validation, no state change)."""
        return cls(
            id=document_id,
            document_type=document_type,
            competition_id=competition_id,
            submission_id=submission_id,
            template_id=template_id,
            snapshot=snapshot,
            created_at=created_at,
            updated_at=updated_at,
            pdf_path=pdf_path,
            published_at=published_at,
            version=version,
        )

    @property
    def is_published(self) -> bool:
        """Whether the participant can see this document."""
        return self.published_at is not None

    def with_pdf(self, path: str, *, now: datetime) -> IssuedDocument:
        """Record the rendered PDF, publishing it if the kind publishes on generation.

        This is where "a thank-you letter appears in the cabinet with no organizer
        action" actually happens — and it is the policy that decides, not this
        method knowing anything about thank-you letters.
        """
        policy = policy_for(self.document_type)
        published_at = now if policy.publishes_on_generation else self.published_at
        return replace(
            self,
            pdf_path=path,
            published_at=published_at,
            updated_at=now,
            version=self.version + 1,
        )
