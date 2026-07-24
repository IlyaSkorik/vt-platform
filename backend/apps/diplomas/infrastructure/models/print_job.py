"""``PrintJobModel`` — tracks one background print-package generation.

Persistence model only. A print-package run (create missing diplomas for a
competition, render each pre-ceremony PDF without a degree, bundle a ZIP) is done
asynchronously; this row is the job's durable status and result, so the client
can poll it and it survives a worker restart.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["PrintJobModel", "PrintJobStatusChoices"]


class PrintJobStatusChoices(models.TextChoices):
    """Lifecycle of a print-package job."""

    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class PrintJobModel(BasePersistenceModel):
    """Database row for a print-package generation job (persistence only)."""

    competition_id = models.UUIDField()
    # Nominations (category ids) the run targets; empty means every nomination
    # of the competition that has an assigned template.
    category_ids = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16,
        choices=PrintJobStatusChoices.choices,
        default=PrintJobStatusChoices.PENDING,
    )
    created_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    zip_path = models.CharField(max_length=1024, blank=True, default="")
    error = models.TextField(blank=True, default="")

    class Meta(BasePersistenceModel.Meta):
        db_table = "diplomas_print_job"
        verbose_name = "print job"
        verbose_name_plural = "print jobs"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=PrintJobStatusChoices.values),
                name="diplomas_print_job_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"PrintJob {self.id} ({self.status})"
