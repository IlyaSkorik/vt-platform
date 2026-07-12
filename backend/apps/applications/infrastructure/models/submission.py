"""``SubmissionModel`` - persistence representation of the ``Submission`` aggregate.

Persistence model only (no invariants/transitions - the domain owns those). The
aggregate's child collections and embedded value objects (the performance, the
participants, teachers, attachments, reviews and the price snapshot) are stored as
JSON on the parent row, because a submission is always loaded and saved as one unit
and its children are never queried independently (the same aggregate-as-a-document
approach the Competitions context uses for its settings/config JSON). The queryable
facts - competition, applicant, status - are ordinary indexed columns.
"""

from __future__ import annotations

from django.db import models

from apps.applications.domain.value_objects import SubmissionStatus

from .base import BasePersistenceModel

__all__ = ["SubmissionModel"]

_STATUS_CHOICES = [(status.value, status.name.title()) for status in SubmissionStatus]


class SubmissionModel(BasePersistenceModel):
    """Database row for a submission (persistence only - no business logic)."""

    competition_id = models.UUIDField()
    applicant_id = models.UUIDField()
    status = models.CharField(max_length=24, choices=_STATUS_CHOICES)

    performance = models.JSONField(null=True, blank=True, default=None)
    participants = models.JSONField(default=list, blank=True)
    teachers = models.JSONField(default=list, blank=True)
    attachments = models.JSONField(default=list, blank=True)
    reviews = models.JSONField(default=list, blank=True)
    price_snapshot = models.JSONField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "applications_submission"
        verbose_name = "submission"
        verbose_name_plural = "submissions"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["applicant_id", "status"]),
            models.Index(fields=["competition_id", "status"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in SubmissionStatus]),
                name="applications_submission_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Submission {self.id} ({self.status})"
