"""``GuardianLinkModel`` — persistence row for a guardian relationship.

Maps the :class:`~apps.participants.domain.value_objects.GuardianLink` value objects
owned by the ``Participant`` aggregate (GUARDIAN_RELATIONSHIP — DIA-001 §4.2). Each
row belongs to exactly one participant; the pair ``(participant, guardian_id)`` is
unique, since a participant may link a given guardian at most once (PRT-008). This
is a **persistence model only** — no business logic. The mapper reconstructs the
aggregate's guardian links from these rows and the repository synchronizes them
when the aggregate is saved.
"""

from __future__ import annotations

from django.db import models

from apps.participants.domain.value_objects import GuardianRelationshipType, RelationshipStatus

from .base import BasePersistenceModel

__all__ = ["GuardianLinkModel"]

_TYPE_CHOICES = [(t.value, t.name.title()) for t in GuardianRelationshipType]
_STATUS_CHOICES = [(s.value, s.name.title()) for s in RelationshipStatus]


class GuardianLinkModel(BasePersistenceModel):
    """Database row for a guardian↔participant relationship (persistence only)."""

    participant = models.ForeignKey(
        "participants.ParticipantModel",
        on_delete=models.CASCADE,
        related_name="guardian_links",
    )
    guardian_id = models.UUIDField()
    relationship_type = models.CharField(max_length=16, choices=_TYPE_CHOICES)
    status = models.CharField(max_length=16, choices=_STATUS_CHOICES)
    established_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "participants_guardian_link"
        verbose_name = "guardian link"
        verbose_name_plural = "guardian links"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["guardian_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["participant", "guardian_id"],
                name="participants_unique_guardian_per_participant",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in RelationshipStatus]),
                name="participants_guardian_link_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    relationship_type__in=[t.value for t in GuardianRelationshipType]
                ),
                name="participants_guardian_link_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.guardian_id} -> {self.participant_id} ({self.status})"
