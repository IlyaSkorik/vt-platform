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
    status_history = models.JSONField(default=list, blank=True)
    missing_files_requests = models.JSONField(default=list, blank=True)
    organizer_notes = models.JSONField(default=list, blank=True)
    participant_messages = models.JSONField(default=list, blank=True)
    # Corrections the organizer made to the entry on the applicant's behalf: what
    # moved, who moved it and when. Kept apart from ``organizer_notes`` (an internal
    # memo) and from ``participant_messages`` (something said to the applicant) —
    # this is the record of the entry itself being rewritten, and both the card's
    # history and the applicant's own view of the order read it.
    organizer_edits = models.JSONField(default=list, blank=True)

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
