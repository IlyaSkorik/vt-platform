"""``ApplicationModel`` - persistence representation of the ``Application`` (order) aggregate.

Persistence model only. The order's cached submission references, service lines,
consents, total price snapshot and status history are stored as JSON on the parent
row (the aggregate is always loaded/saved whole); the queryable facts - competition,
applicant, status - are ordinary indexed columns. The educational-organization
reference is kept as an id column plus its frozen name snapshot.
"""

from __future__ import annotations

from django.db import models

from apps.applications.domain.value_objects import ApplicationStatus

from .base import BasePersistenceModel

__all__ = ["ApplicationModel"]

_STATUS_CHOICES = [(status.value, status.name.title()) for status in ApplicationStatus]


class ApplicationModel(BasePersistenceModel):
    """Database row for an application/order (persistence only - no business logic)."""

    competition_id = models.UUIDField()
    applicant_id = models.UUIDField()
    status = models.CharField(max_length=24, choices=_STATUS_CHOICES)

    educational_organization_id = models.UUIDField(null=True, blank=True, default=None)
    organization_name = models.CharField(max_length=300, null=True, blank=True, default=None)

    submission_refs = models.JSONField(default=list, blank=True)
    service_lines = models.JSONField(default=list, blank=True)
    consents = models.JSONField(default=list, blank=True)
    total_price = models.JSONField(null=True, blank=True, default=None)
    status_history = models.JSONField(default=list, blank=True)
    # A list, not one document: an order's fee is regularly settled by several
    # transfers, and each produces its own slip.
    payment_receipts = models.JSONField(default=list, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True, default=None)
    # When the order was submitted; drives the unpaid auto-cancel sweep.
    submitted_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "applications_application"
        verbose_name = "application"
        verbose_name_plural = "applications"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["applicant_id", "status"]),
            models.Index(fields=["competition_id", "status"]),
            models.Index(fields=["status", "submitted_at"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in ApplicationStatus]),
                name="applications_application_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Application {self.id} ({self.status})"
