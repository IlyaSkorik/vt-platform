"""``DiplomaModel`` — persistence for the :class:`Diploma` aggregate root.

Persistence model only (no business logic). A diploma is **self-contained**: it
stores a frozen :attr:`snapshot` of the data it was created from, so later edits
to the submission or competition never change it. Cross-context references
(``competition_id``, ``submission_id``, ``template_id``) are id-only plain
``UUIDField`` columns (ARCH-001 §7.2) — never FKs — which also keeps a diploma
independent of the rows it was derived from.

``number`` and ``verification_token`` are globally unique and permanent (a number
is never reused, even after a soft delete), enforced by unconditional unique
constraints.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel
from .document_type import DocumentTypeChoices

__all__ = ["DiplomaModel", "DiplomaStatusChoices"]


class DiplomaStatusChoices(models.TextChoices):
    """Diploma lifecycle states (mirrors the domain ``DiplomaStatus``)."""

    DRAFT = "DRAFT", "Draft"
    GENERATED = "GENERATED", "Generated"
    ISSUED = "ISSUED", "Issued"
    CANCELLED = "CANCELLED", "Cancelled"


class DiplomaModel(BasePersistenceModel):
    """Database row for a diploma (persistence only - no business logic)."""

    # Permanent, globally unique human-facing number and QR verification token.
    number = models.CharField(max_length=64)
    verification_token = models.CharField(max_length=64)

    # Which numbered, verifiable kind this row is: the performance's own diploma, or
    # the individual diploma of one named member of its collective. Both belong here
    # because both draw a registry number and a verification token.
    document_type = models.CharField(max_length=32, choices=DocumentTypeChoices.choices, default=DocumentTypeChoices.DIPLOMA)

    # Who the diploma is for, for a kind issued per member of a collective; empty for
    # the performance's own diploma. Part of the row's identity — see the unique
    # constraint below.
    recipient = models.CharField(max_length=320, blank=True, default="")

    # Id-only cross-context references (not FKs) — a diploma stands alone.
    competition_id = models.UUIDField()
    submission_id = models.UUIDField()
    template_id = models.UUIDField()

    status = models.CharField(
        max_length=16,
        choices=DiplomaStatusChoices.choices,
        default=DiplomaStatusChoices.DRAFT,
    )

    # The frozen dataset the diploma is printed from — one JSON document, so new
    # snapshot fields need no migration (the aggregate-as-document approach the
    # Submission uses). award.degree inside may be null until the jury decides.
    snapshot = models.JSONField(default=dict, blank=True)

    # Rendered PDFs. The print PDF is the pre-ceremony copy WITHOUT a degree; the
    # official PDF is produced after the jury assigns the degree. Empty until each
    # is generated. Two columns now so the second branch needs no later migration.
    print_pdf_path = models.CharField(max_length=1024, blank=True, default="")
    official_pdf_path = models.CharField(max_length=1024, blank=True, default="")
    issued_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_diploma"
        verbose_name = "diploma"
        verbose_name_plural = "diplomas"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
            models.Index(fields=["submission_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["document_type"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(fields=["number"], name="diplomas_diploma_number_unique"),
            models.UniqueConstraint(fields=["verification_token"], name="diplomas_diploma_token_unique"),
            # At most one live diploma per performance, kind **and recipient**. For the
            # performance's own diploma the recipient is empty, which reduces to the
            # original "one diploma per submission" rule; for an individual diploma it
            # is what lets every named member of a collective hold their own.
            models.UniqueConstraint(
                fields=["submission_id", "document_type", "recipient"],
                condition=models.Q(deleted_at__isnull=True),
                name="diplomas_diploma_unique_per_recipient",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=DiplomaStatusChoices.values),
                name="diplomas_diploma_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(document_type__in=DocumentTypeChoices.values),
                name="diplomas_diploma_document_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Diploma {self.number} ({self.status})"
