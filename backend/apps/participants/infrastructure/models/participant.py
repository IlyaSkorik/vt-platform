"""``ParticipantModel`` — persistence representation of the ``Participant`` aggregate root.

Maps every field of the ``apps.participants.domain.entities.Participant`` aggregate
to a column (PARTICIPANT — DIA-001 §4.2). This is a **persistence model only**: it
holds no invariants, transitions, or validation — the domain aggregate owns all of
that. The mapper/repository projects a ``Participant`` onto these columns (plus its
guardian-link child rows) and rehydrates it back.

Uniqueness of the pseudonymized display alias is enforced only among **active,
non-erased** rows via a partial unique constraint, so an alias frees up once a
participant is erased/soft-deleted while remaining unique among live participants.
The real name is stored under strict access control at the application/presentation
edge (PRT-006); the column itself is ordinary.
"""

from __future__ import annotations

from django.db import models

from apps.participants.domain.value_objects import ActorType, ParticipantStatus

from .base import BasePersistenceModel

__all__ = ["ParticipantModel"]

_STATUS_CHOICES = [(status.value, status.name.title()) for status in ParticipantStatus]
_ACTOR_CHOICES = [(actor.value, actor.name.title()) for actor in ActorType]


class ParticipantModel(BasePersistenceModel):
    """Database row for a participant (persistence only — no business logic)."""

    # Minimized personal identity (``PersonName`` value object).
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True, default=None)

    # Age-group source (``DateOfBirth``) and the pseudonym shown to judging.
    date_of_birth = models.DateField()
    display_alias = models.CharField(max_length=64)

    # Lifecycle state (DATA-004 §4.3).
    status = models.CharField(max_length=16, choices=_STATUS_CHOICES)

    # Creating actor (``ActorReference``).
    created_by_id = models.UUIDField()
    created_by_type = models.CharField(max_length=16, choices=_ACTOR_CHOICES)

    # Institutional authority (``InstitutionAuthority``), if any.
    institution_id = models.UUIDField(null=True, blank=True, default=None)
    teacher_id = models.UUIDField(null=True, blank=True, default=None)

    # Recorded consent reference (``ConsentReference``), if any.
    consent_id = models.UUIDField(null=True, blank=True, default=None)
    consent_version = models.CharField(max_length=64, null=True, blank=True, default=None)

    # Lifecycle timestamps (all authoritative on the aggregate).
    verified_at = models.DateTimeField(null=True, blank=True, default=None)
    activated_at = models.DateTimeField(null=True, blank=True, default=None)
    archived_at = models.DateTimeField(null=True, blank=True, default=None)
    erased_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "participants_participant"
        verbose_name = "participant"
        verbose_name_plural = "participants"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["display_alias"]),
            models.Index(fields=["status"]),
            models.Index(fields=["institution_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["display_alias"],
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(status="erased"),
                name="participants_unique_active_display_alias",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in ParticipantStatus]),
                name="participants_participant_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(created_by_type__in=[a.value for a in ActorType]),
                name="participants_participant_actor_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.display_alias} ({self.id})"
