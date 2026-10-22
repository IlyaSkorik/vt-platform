"""``DocumentJobModel`` — tracks one background non-registry generation run.

Persistence model only. Generating a genre's thank-you letters renders a PDF per
recipient and, when asked, bundles a ZIP — minutes of work for a festival, which
is longer than any proxy between the organizer and the worker is willing to hold
a connection open. So the run is done asynchronously and this row is its durable
status and result: the client polls it, and it survives a worker restart.

Deliberately **not** :class:`PrintJobModel` with extra columns. That job's result
is the diploma package's — created, skipped, one ZIP — while this one answers a
different question per kind (addressed to nobody, left unpublished, already held).
Sharing the row would mean half its columns were always null, and which half
would depend on which kind of run wrote it.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel
from .document_type import DocumentTypeChoices
from .print_job import PrintJobStatusChoices

__all__ = ["DocumentJobModel"]


class DocumentJobModel(BasePersistenceModel):
    """Database row for one non-registry generation job (persistence only)."""

    competition_id = models.UUIDField()
    # Genres (category ids) the run targets. Never empty: unlike the print package,
    # a document run is always asked for by nomination.
    category_ids = models.JSONField(default=list, blank=True)
    document_type = models.CharField(max_length=32, choices=DocumentTypeChoices.choices)

    # The run's three independent switches, exactly as the request named them.
    force = models.BooleanField(default=False)
    bundle = models.BooleanField(default=False)
    publish = models.BooleanField(default=True)

    # Shared with the print package: a job's lifecycle is the same whatever it runs.
    status = models.CharField(
        max_length=16,
        choices=PrintJobStatusChoices.choices,
        default=PrintJobStatusChoices.PENDING,
    )

    # The summary the run produced, stored whole rather than spread over columns.
    # It is what the endpoint used to answer with directly, so a client polling the
    # job reads the same object it once got back from the request — and a kind that
    # grows a new counter does not grow a migration. Empty until the run completes.
    result = models.JSONField(default=dict, blank=True)

    error = models.TextField(blank=True, default="")

    # Who asked for the run. Recorded here because the request knows the requester
    # and the worker does not, and carried into the generation archive when the job
    # completes.
    actor_id = models.UUIDField(null=True, blank=True, default=None)
    actor_label = models.CharField(max_length=320, blank=True, default="")

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_document_job"
        verbose_name = "document job"
        verbose_name_plural = "document jobs"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=PrintJobStatusChoices.values),
                name="diplomas_document_job_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(document_type__in=DocumentTypeChoices.values),
                name="diplomas_document_job_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"DocumentJob {self.id} ({self.document_type}, {self.status})"
