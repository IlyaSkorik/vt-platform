"""``IssuedDocumentModel`` — persistence for the :class:`IssuedDocument` aggregate.

Persistence model only (no business logic). Holds every generated document whose
kind needs neither a number nor verification — the thank-you letter today, a
certificate tomorrow. The numbered, verifiable diploma keeps its own table
(``diplomas_diploma``), which this change does not touch.

Deliberately **not** a diploma with nullable columns: a diploma's number and
verification token are permanent and unique, and relaxing them to hold courtesy
letters would drop the very invariants the public register depends on.

Like a diploma it stores a frozen :attr:`snapshot`, so later edits to the
submission or competition never change an issued document, and cross-context
references (``competition_id``, ``submission_id``, ``template_id``) are id-only
plain ``UUIDField`` columns (ARCH-001 §7.2) — never FKs.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel
from .document_type import DocumentTypeChoices

__all__ = ["IssuedDocumentModel"]


class IssuedDocumentModel(BasePersistenceModel):
    """Database row for a generated non-registry document (persistence only)."""

    document_type = models.CharField(max_length=32, choices=DocumentTypeChoices.choices)

    # Id-only cross-context references (not FKs) — a document stands alone.
    competition_id = models.UUIDField()
    submission_id = models.UUIDField()
    template_id = models.UUIDField()

    # Who the document is addressed to — a teacher's name for a per-teacher kind,
    # empty for a kind issued once per performance. Part of the row's identity, so
    # two teachers on one entry are two letters rather than one overwriting the other.
    recipient = models.CharField(max_length=320, blank=True, default="")

    # The frozen dataset the document was rendered from.
    snapshot = models.JSONField(default=dict, blank=True)

    # The rendered PDF, empty until generation completes.
    pdf_path = models.CharField(max_length=1024, blank=True, default="")

    # Set the moment the document becomes visible to the participant. For kinds
    # that publish on generation this is stamped by the same transition that
    # records the PDF, so no organizer action stands between the two.
    published_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_issued_document"
        verbose_name = "issued document"
        verbose_name_plural = "issued documents"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
            models.Index(fields=["submission_id"]),
            models.Index(fields=["document_type"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            # At most one live document per performance, kind **and recipient**. For a
            # kind issued once per performance the recipient is empty, which reduces
            # to the diploma's own rule; for a per-teacher kind it is what lets two
            # teachers hold two separate letters.
            models.UniqueConstraint(
                fields=["submission_id", "document_type", "recipient"],
                condition=models.Q(deleted_at__isnull=True),
                name="diplomas_issued_unique_per_recipient",
            ),
            models.CheckConstraint(
                condition=models.Q(document_type__in=DocumentTypeChoices.values),
                name="diplomas_issued_document_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document_type} for submission {self.submission_id}"
