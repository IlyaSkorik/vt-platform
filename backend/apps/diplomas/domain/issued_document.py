"""The ``IssuedDocument`` aggregate — a generated document that is not a diploma.

Hosts every document kind whose :class:`~apps.diplomas.domain.document_types.DocumentPolicy`
asks for neither a number nor verification: today the thank-you letter, tomorrow a
certificate. The ``Diploma`` aggregate keeps the numbered, verifiable registry to
itself and is untouched by this.

Like a diploma, an issued document is **self-contained**: it freezes the
:class:`DiplomaSnapshot` it was generated from, so later edits to the submission or
the competition never change it. Unlike a diploma it has no number, no verification
token and no public register entry — and when its policy allows it, the generating
run can publish it outright, with no separate organizer step. Whether a given run
does is the run's call: sheets prepared for printing stay out of the cabinet until
someone publishes them.

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
    #: Who this document is addressed to — a teacher's name for a per-teacher kind,
    #: empty for a kind issued once per performance. Part of the document's identity:
    #: for a per-teacher kind it is what makes the document the *teacher's* rather
    #: than any one entry's (see :attr:`category_id`).
    recipient: str = ""
    #: The genre this document was issued for. ``None`` only on rows written before
    #: the column existed.
    #:
    #: A per-teacher document is identified by ``(competition, genre, recipient)``:
    #: a teacher who entered five acts in one genre is thanked once, and
    #: ``submission_id`` then records merely which of those five the sheet was built
    #: from. A kind issued once per performance ignores this entirely and stays
    #: identified by its submission.
    category_id: uuid.UUID | None = None
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
        recipient: str = "",
        category_id: uuid.UUID | None = None,
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
            recipient=recipient,
            category_id=category_id,
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
        recipient: str = "",
        category_id: uuid.UUID | None = None,
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
            recipient=recipient,
            category_id=category_id,
            pdf_path=pdf_path,
            published_at=published_at,
            version=version,
        )

    @property
    def is_published(self) -> bool:
        """Whether the participant can see this document."""
        return self.published_at is not None

    def with_pdf(self, path: str, *, now: datetime, publish: bool = True) -> IssuedDocument:
        """Record the rendered PDF, publishing it unless the caller withholds that.

        Two gates, and both must open. The **policy** says whether the kind may be
        published by its generating run at all (a diploma may not — it is published
        through the registry). The **caller** says whether this particular run does:
        an organizer preparing sheets to print is not yet showing them to anyone.

        Publication is one-way here. An already-published document keeps its
        original timestamp, so re-rendering it — with or without ``publish`` — never
        moves the date and never takes it back out of the cabinet. Use
        :meth:`publish` to publish a document that is already rendered.
        """
        policy = policy_for(self.document_type)
        published_at = self.published_at or (now if publish and policy.publishes_on_generation else None)
        return replace(
            self,
            pdf_path=path,
            published_at=published_at,
            updated_at=now,
            version=self.version + 1,
        )

    def publish(self, *, now: datetime) -> IssuedDocument:
        """Publish an already-rendered document, without re-rendering it.

        The second half of the split above: documents generated for print only are
        complete but invisible, and this is what a later "publish" run does to them.
        Idempotent — an already-published document is returned untouched, keeping its
        original publication date.
        """
        if self.published_at is not None:
            return self
        return replace(self, published_at=now, updated_at=now, version=self.version + 1)
