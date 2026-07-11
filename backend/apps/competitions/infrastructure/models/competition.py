"""``CompetitionModel`` — persistence for the :class:`Competition` aggregate root.

Persistence only (ARCH-001 §7.2, §14): no invariants, transitions, or validation —
the domain aggregate owns all of that. The row carries the root's own state; its
child collections live in sibling tables (see :mod:`.taxonomy`, :mod:`.rules`,
:mod:`.content`) keyed by ``competition_id`` and loaded/saved with the root as one
aggregate.

**Column vs JSON choice.** Distinct business fields the domain models as separate
value objects (venue, branding, periods, deadlines) are flattened to explicit,
queryable columns. The cohesive
:class:`~apps.competitions.domain.value_objects.CompetitionSettings` flag bag is
stored as JSON — deliberately append-only/extensible, so a new flag lands without
a schema migration. Participation formats live in their own child table.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["CompetitionModel", "CompetitionStatusChoices"]


class CompetitionStatusChoices(models.TextChoices):
    """Competition lifecycle states (mirrors the domain ``CompetitionStatus``)."""

    DRAFT = "DRAFT", "Draft"
    CONFIGURED = "CONFIGURED", "Configured"
    READY = "READY", "Ready"
    PUBLISHED = "PUBLISHED", "Published"
    REGISTRATION_OPEN = "REGISTRATION_OPEN", "Registration open"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED", "Registration closed"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    ARCHIVED = "ARCHIVED", "Archived"


class CompetitionModel(BasePersistenceModel):
    """Database row for the competition aggregate root (persistence only)."""

    title = models.CharField(max_length=200)
    season = models.CharField(max_length=50)
    organizer_id = models.UUIDField()
    status = models.CharField(
        max_length=32,
        choices=CompetitionStatusChoices.choices,
        default=CompetitionStatusChoices.DRAFT,
    )
    description = models.TextField(null=True, blank=True, default=None)

    # Branding assets (opaque storage references).
    logo = models.CharField(max_length=1024, null=True, blank=True, default=None)
    banner = models.CharField(max_length=1024, null=True, blank=True, default=None)
    poster = models.CharField(max_length=1024, null=True, blank=True, default=None)

    # Venue.
    venue_name = models.CharField(max_length=200, null=True, blank=True, default=None)
    venue_address = models.CharField(max_length=500, null=True, blank=True, default=None)

    # Registration & competition periods (inclusive calendar-date ranges).
    registration_start = models.DateField(null=True, blank=True, default=None)
    registration_end = models.DateField(null=True, blank=True, default=None)
    competition_start = models.DateField(null=True, blank=True, default=None)
    competition_end = models.DateField(null=True, blank=True, default=None)

    # Registration deadlines (each an optional cut-off instant).
    deadline_application = models.DateTimeField(null=True, blank=True, default=None)
    deadline_payment = models.DateTimeField(null=True, blank=True, default=None)
    deadline_music_upload = models.DateTimeField(null=True, blank=True, default=None)
    deadline_document_upload = models.DateTimeField(null=True, blank=True, default=None)
    deadline_correction = models.DateTimeField(null=True, blank=True, default=None)

    # Cohesive value bags stored as JSON (see module docstring).
    settings = models.JSONField(default=dict)
    contacts_config = models.JSONField(default=dict)
    landing_config = models.JSONField(default=dict)

    # Pointer to the current regulation version (a child row in competitions_regulation).
    current_regulation_id = models.UUIDField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "competitions_competition"
        verbose_name = "competition"
        verbose_name_plural = "competitions"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["organizer_id"]),
            models.Index(fields=["season"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status__in=CompetitionStatusChoices.values),
                name="competitions_competition_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.season})"
